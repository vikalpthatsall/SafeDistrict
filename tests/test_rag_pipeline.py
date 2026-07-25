from unittest.mock import Mock

import pandas as pd
import pytest
from langchain_core.documents import Document

from backend.config import Settings
from backend.rag_pipeline import (
    RAGPipeline,
    build_crime_documents,
    build_key_findings_document,
)

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


def test_rag_pipeline_query_shape() -> None:
    pipeline = RAGPipeline.__new__(RAGPipeline)

    fake_docs = [
        Document(page_content="doc one content"),
        Document(page_content="doc two content"),
        Document(page_content="doc three content"),
    ]
    pipeline.retriever = Mock()
    pipeline.retriever.invoke = Mock(return_value=fake_docs)

    pipeline.llm = Mock()
    pipeline.llm.invoke = Mock(return_value=Mock(content="a fake generated answer"))

    result = pipeline.query("Is Testville safe?")

    assert result["question"] == "Is Testville safe?"
    assert result["answer"] == "a fake generated answer"
    assert result["num_sources"] == len(fake_docs)
    assert len(result["sources"]) == len(fake_docs)
    assert "data_citation" in result
    assert "source_url" in result
