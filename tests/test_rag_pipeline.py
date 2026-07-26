import asyncio
from unittest.mock import AsyncMock, Mock

import httpx
import pandas as pd
import pytest
import tenacity
from groq import APIConnectionError
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from backend.config import Settings
from backend.rag_pipeline import (
    RAGPipeline,
    _min_max_normalize,
    build_crime_documents,
    build_key_findings_document,
)


def _transient_groq_error() -> APIConnectionError:
    """A minimal, real groq SDK exception — same type RAGPipeline retries on."""
    return APIConnectionError(request=httpx.Request("POST", "https://api.groq.com"))


@pytest.fixture
def no_retry_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip real exponential backoff (1s/2s/4s) in tests that exhaust retries.

    tenacity exposes the AsyncRetrying instance as `<method>.retry`, with a
    mutable `.wait` — the officially documented way to override retry timing
    per-test without touching the decorator itself.
    """
    monkeypatch.setattr(RAGPipeline._invoke_groq.retry, "wait", tenacity.wait_none())


_ROW_COLUMNS = [
    "city", "state", "murder", "rape", "kidnapping", "robbery",
    "burglary", "vehicle_theft", "total_ipc", "crimes_per_lakh", "data_quality",
]


def _row(city: str, data_quality: str) -> dict:
    return {
        "city": city,
        "state": "TestState",
        "murder": 10,
        "rape": 20,
        "kidnapping": 15,
        "robbery": 30,
        "burglary": 40,
        "vehicle_theft": 25,
        "total_ipc": 500,
        "crimes_per_lakh": 123.4,
        "data_quality": data_quality,
    }


@pytest.fixture
def tiered_df() -> pd.DataFrame:
    rows = [
        _row("RealCity", "real"),
        _row("DerivedCity", "derived"),
        _row("EstimatedCity", "estimated"),
        _row("NationalCity", "national"),
    ]
    return pd.DataFrame(rows, columns=_ROW_COLUMNS)


def test_build_crime_documents_citation_tags(tiered_df: pd.DataFrame) -> None:
    docs = build_crime_documents(tiered_df)
    tags = [
        "[NCRB 2023 verified]",
        "[derived from NCRB 2023 murder rates]",
        "[estimated from NCRB 2023 state ratios]",
        "[estimated from NCRB 2023 national ratios — lowest confidence]",
    ]
    for doc, tag in zip(docs, tags):
        assert doc.startswith(tag)
    # all four tiers must be visibly distinct citations, not just distinct data_quality values
    assert len(set(tags)) == 4


def test_build_key_findings_document() -> None:
    facts = ["Fact one about crime.", "Fact two about safety."]
    doc = build_key_findings_document(facts)
    assert "NCRB Crime in India 2023" in doc
    for fact in facts:
        assert fact in doc


def test_settings_raises_without_groq_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # RAGPipeline no longer checks GROQ_API_KEY itself — it trusts backend.config.settings,
    # which is a module-level singleton built once at import time. That means monkeypatching
    # the env var *after* backend.config has already been imported has no effect on the
    # existing `settings` object, so the missing-key behavior can only be tested by
    # constructing a fresh Settings() here, not via RAGPipeline(...) as before.
    # _env_file=None guards against a real local .env file masking the missing var.
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(OSError):
        Settings(_env_file=None)


def _pipeline_with_mocks(fake_texts: list[str]) -> RAGPipeline:
    """RAGPipeline with retrieve() itself mocked — for tests about generation
    (LLM call, retry, fallback), not retrieval. retrieve()'s own internals
    (hybrid search, reranking) are covered separately, below.
    """
    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline.retrieve = AsyncMock(
        return_value=[{"text": t, "score": 1.0} for t in fake_texts]
    )
    pipeline.llm = Mock()
    pipeline.fallback_llm = None
    return pipeline


def test_rag_pipeline_query_shape() -> None:
    # No pytest-asyncio in requirements.txt, so this stays a plain sync test
    # function and drives the coroutine itself via asyncio.run(), rather than
    # adding a new test-only dependency for one test.
    fake_texts = ["doc one content", "doc two content", "doc three content"]
    pipeline = _pipeline_with_mocks(fake_texts)
    pipeline.llm.ainvoke = AsyncMock(return_value=Mock(content="a fake generated answer"))

    result = asyncio.run(pipeline.aquery("Is Testville safe?"))

    assert result["question"] == "Is Testville safe?"
    assert result["answer"] == "a fake generated answer"
    assert result["num_sources"] == len(fake_texts)
    assert len(result["sources"]) == len(fake_texts)
    assert "data_citation" in result
    assert "source_url" in result
    # successful first attempt — retry must not fire extra calls
    assert pipeline.llm.ainvoke.call_count == 1


def test_aquery_retries_groq_four_times_then_raises(no_retry_wait: None) -> None:
    pipeline = _pipeline_with_mocks(["doc content"])
    pipeline.llm.ainvoke = AsyncMock(side_effect=_transient_groq_error())
    # no fallback configured — retry-then-raise is the whole story here

    with pytest.raises(APIConnectionError):
        asyncio.run(pipeline.aquery("Is Testville safe?"))

    assert pipeline.llm.ainvoke.call_count == 4


def test_aquery_falls_back_to_anthropic_after_groq_exhausted(no_retry_wait: None) -> None:
    pipeline = _pipeline_with_mocks(["doc content"])
    pipeline.llm.ainvoke = AsyncMock(side_effect=_transient_groq_error())
    pipeline.fallback_llm = Mock()
    pipeline.fallback_llm.ainvoke = AsyncMock(return_value=Mock(content="fallback answer"))

    result = asyncio.run(pipeline.aquery("Is Testville safe?"))

    assert result["answer"] == "fallback answer"
    assert pipeline.llm.ainvoke.call_count == 4
    pipeline.fallback_llm.ainvoke.assert_called_once()


# ---------------------------------------------------------------------------
# Hybrid search: BM25 + vector score combination
# ---------------------------------------------------------------------------

def test_hybrid_search_combines_bm25_and_vector_scores() -> None:
    corpus = [
        "Mumbai has a low crime rate and is very safe for families",
        "Delhi reports high crime including robbery and theft",
        "Pune is a quiet city with minimal crime reports",
    ]
    query = "Delhi crime"

    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline.bm25_retriever = BM25Retriever.from_texts(corpus)

    # Compute BM25's real scores independently, via the same retriever
    # instance _hybrid_search will use — this checks the *combination
    # formula* against real BM25 output, not a hand-guessed number.
    bm25_raw = pipeline.bm25_retriever.vectorizer.get_scores(
        pipeline.bm25_retriever.preprocess_func(query)
    )
    bm25_by_text = {text: float(score) for text, score in zip(corpus, bm25_raw)}
    bm25_norm = _min_max_normalize(bm25_by_text)

    # Deliberately scored so the vector signal disagrees with BM25's ranking —
    # if _hybrid_search silently used only one signal, this test would catch it.
    vector_scores = {corpus[0]: 0.9, corpus[1]: 0.5, corpus[2]: 0.3}
    pipeline.vector_store = Mock()
    pipeline.vector_store.asimilarity_search_with_relevance_scores = AsyncMock(
        return_value=[(Document(page_content=t), s) for t, s in vector_scores.items()]
    )

    results = asyncio.run(pipeline._hybrid_search(query))
    scores_by_text = {r["text"]: r["score"] for r in results}

    assert set(scores_by_text) == set(corpus)
    for text in corpus:
        expected = 0.6 * vector_scores[text] + 0.4 * bm25_norm[text]
        assert scores_by_text[text] == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Reranking
# ---------------------------------------------------------------------------

def test_rerank_changes_top5_order() -> None:
    # Candidates in hybrid-search order: a semantically-fluffy doc ranked
    # above an exact keyword match for "Delhi crime" — a realistic failure
    # mode for vector/BM25 blending alone.
    candidates = [
        {"text": "Family-friendly neighborhoods with good schools nearby", "score": 0.8},
        {"text": "Delhi crime rate: 506 murders, 1088 rapes reported in 2023", "score": 0.5},
        {"text": "Pune is quiet and pleasant for relocation", "score": 0.3},
    ]

    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline._cross_encoder = Mock()
    # The (mocked) cross-encoder correctly favors the exact keyword match,
    # even though it ranked second in the hybrid stage.
    pipeline._cross_encoder.predict = Mock(return_value=[0.1, 0.95, 0.2])

    reranked = asyncio.run(pipeline._rerank("Delhi crime", candidates))

    assert [r["text"] for r in reranked] != [c["text"] for c in candidates]
    assert reranked[0]["text"] == candidates[1]["text"]
    assert reranked[0]["score"] == pytest.approx(0.95)
