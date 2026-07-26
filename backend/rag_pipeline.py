"""
rag_pipeline.py — RAG pipeline for SafeDistrict AI.

Embeds NCRB 2023 city crime documents into ChromaDB using free
HuggingFace embeddings, then answers natural-language safety
queries via ChatGroq (llama-3.3-70b-versatile).

Retrieval is hybrid (BM25 + vector) with cross-encoder reranking — see
RAGPipeline.retrieve(). Reranking uses sentence-transformers' CrossEncoder,
which imports torch unconditionally regardless of its `backend=` argument
(verified against the installed source, not assumed). requirements.txt
(dev) already includes torch, but requirements-prod.txt deliberately does
not (CPU-only ONNX embeddings) — this feature does not currently work
against the deployed HF Space's production dependency set. That tradeoff
is intentionally left for a separate decision rather than silently adding
torch back to requirements-prod.txt here.

Every document carries an inline citation tag:
  [NCRB 2023 verified]                              — exact counts from NCRB tables
  [derived from NCRB 2023 murder rates]              — computed from rate × population
  [estimated from NCRB 2023 state ratios]            — state-level ratio × total IPC
  [estimated from NCRB 2023 national ratios — lowest confidence] — national ratio × total IPC (fallback)

Every query response includes data_citation and source_url fields.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from groq import APIConnectionError, APITimeoutError, RateLimitError
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.config import get_settings

_DATA_CITATION = "NCRB Crime in India 2023"
_SOURCE_URL = "https://data.opencity.in/dataset/crime-in-india-2023"

# Transient-looking Groq failures worth retrying — not auth/validation errors,
# which retrying can't fix.
_TRANSIENT_GROQ_ERRORS = (APIConnectionError, APITimeoutError, RateLimitError)

# Hybrid retrieval — exact weights from the interview material.
_VECTOR_WEIGHT = 0.6
_BM25_WEIGHT = 0.4
_CANDIDATE_POOL_SIZE = 15
_FINAL_TOP_K = 5
_RERANKER_MODEL = "BAAI/bge-reranker-base"


def _min_max_normalize(scores: dict[str, float]) -> dict[str, float]:
    """Scale raw scores to [0, 1].

    BM25 scores are unbounded, unlike Chroma's already-normalized relevance
    scores — this makes the two comparable before combining them with fixed
    weights.
    """
    if not scores:
        return {}
    values = list(scores.values())
    lo, hi = min(values), max(values)
    if hi == lo:
        return dict.fromkeys(scores, 0.0)
    return {key: (value - lo) / (hi - lo) for key, value in scores.items()}


# ---------------------------------------------------------------------------
# Document builders
# ---------------------------------------------------------------------------

def build_crime_documents(df: pd.DataFrame) -> list[str]:
    """Convert each city row into a human-readable text document with citation tag.

    Parameters
    ----------
    df : pd.DataFrame
        Enriched NCRB DataFrame from CrimeDataLoader (must include data_quality column).

    Returns
    -------
    list[str]
        One document string per city.
    """
    docs = []
    for _, row in df.iterrows():
        quality = row.get("data_quality", "estimated")
        if quality == "real":
            citation = "[NCRB 2023 verified]"
        elif quality == "derived":
            citation = "[derived from NCRB 2023 murder rates]"
        elif quality == "national":
            citation = "[estimated from NCRB 2023 national ratios — lowest confidence]"
        else:
            citation = "[estimated from NCRB 2023 state ratios]"

        women_crimes = int(row["rape"]) + int(row["kidnapping"])
        doc = (
            f"{citation} In 2023, {row['city']} ({row['state']}) reported "
            f"{int(row['total_ipc'])} total IPC crimes. "
            f"Crime breakdown: {int(row['murder'])} murders, "
            f"{int(row['rape'])} rapes, {int(row['kidnapping'])} kidnappings, "
            f"{int(row['robbery'])} robberies, {int(row['burglary'])} burglaries, "
            f"{int(row['vehicle_theft'])} vehicle thefts. "
            f"Crimes per lakh population: {row['crimes_per_lakh']}. "
            f"Women-specific crimes (rape + kidnapping): {women_crimes}."
        )
        docs.append(doc)
    return docs


def build_key_findings_document(key_findings: list[str]) -> str:
    """Build a single context document from the list of NCRB key findings.

    Parameters
    ----------
    key_findings : list[str]
        Verified facts from NCRB_2023_KEY_FINDINGS.

    Returns
    -------
    str
        Formatted document string to embed alongside city documents.
    """
    facts = "\n".join(f"- {f}" for f in key_findings)
    return (
        f"[NCRB 2023 verified] Key findings from {_DATA_CITATION} ({_SOURCE_URL}):\n"
        + facts
    )


# ---------------------------------------------------------------------------
# Vector store helpers
# ---------------------------------------------------------------------------

def _get_embeddings() -> HuggingFaceEmbeddings:
    """Return HuggingFace embeddings (downloads ~90 MB on first use)."""
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def build_vector_store(
    documents: list[str],
    persist_dir: str = "chromadb/",
) -> Chroma:
    """Embed documents and persist a Chroma vector store.

    Parameters
    ----------
    documents : list[str]
        Plain-text documents (city docs + optional key_findings doc).
    persist_dir : str
        Directory path for ChromaDB persistence.

    Returns
    -------
    Chroma
        Populated, persisted vector store.
    """
    embeddings = _get_embeddings()
    store = Chroma.from_texts(
        texts=documents,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name="ncrb_2023",
    )
    return store


def load_vector_store(persist_dir: str = "chromadb/") -> Chroma:
    """Load an existing Chroma vector store from disk.

    Parameters
    ----------
    persist_dir : str
        Directory path used when build_vector_store() was called.

    Returns
    -------
    Chroma
        Loaded vector store ready for similarity search.
    """
    embeddings = _get_embeddings()
    return Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
        collection_name="ncrb_2023",
    )


# ---------------------------------------------------------------------------
# RAGPipeline
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are SafeDistrict AI, a crime safety assistant for Indian cities. "
    "Answer using ONLY the provided NCRB 2023 crime data. "
    "When data is marked [NCRB 2023 verified], cite it as verified. "
    "When data is marked [estimated from NCRB 2023 state ratios], note it is estimated. "
    "Be specific with numbers. If data is not available say so. "
    "Keep answers concise and helpful for relocation decisions."
)


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline over NCRB 2023 city data.

    Uses ChromaDB + HuggingFace embeddings and BM25 for hybrid retrieval,
    a cross-encoder for reranking (see retrieve()), and ChatGroq
    (llama-3.3-70b-versatile) for answer generation.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        rebuild: bool = False,
        persist_dir: str = "chromadb/",
        key_findings: list[str] | None = None,
    ) -> None:
        """Initialise the RAG pipeline.

        Parameters
        ----------
        df : pd.DataFrame
            Enriched NCRB DataFrame from CrimeDataLoader.
        rebuild : bool
            If True, delete existing store and rebuild from df.
        persist_dir : str
            ChromaDB persistence directory.
        key_findings : list[str] | None
            Optional NCRB key findings to embed as an additional context document.
        """
        settings = get_settings()

        # Computed unconditionally (cheap — pure string formatting) so BM25's
        # corpus always matches the current df, regardless of whether the
        # Chroma vector store is freshly built or loaded from disk.
        documents = build_crime_documents(df)
        if key_findings:
            documents.append(build_key_findings_document(key_findings))

        store_exists = Path(persist_dir).exists() and any(Path(persist_dir).iterdir())
        if rebuild or not store_exists:
            print("Building vector store from NCRB documents...")
            store = build_vector_store(documents, persist_dir=persist_dir)
            print(f"  {len(documents)} documents embedded -> {persist_dir}")
        else:
            print(f"Loading existing vector store from {persist_dir}")
            store = load_vector_store(persist_dir=persist_dir)

        self.vector_store = store
        self.bm25_retriever = BM25Retriever.from_texts(documents)

        # See module docstring: requires torch (via sentence-transformers'
        # CrossEncoder), which is not in requirements-prod.txt.
        from sentence_transformers import CrossEncoder

        self._cross_encoder = CrossEncoder(_RERANKER_MODEL)

        self.llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            max_tokens=1024,
            temperature=0,
        )

        self.fallback_llm = None
        if settings.anthropic_api_key:
            from langchain_anthropic import ChatAnthropic

            self.fallback_llm = ChatAnthropic(model=settings.anthropic_model, temperature=0)

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1),
        retry=retry_if_exception_type(_TRANSIENT_GROQ_ERRORS),
        reraise=True,
    )
    async def _invoke_groq(self, messages: list) -> object:
        """Call the Groq LLM, retrying transient failures up to 4 attempts (1s/2s/4s backoff)."""
        return await self.llm.ainvoke(messages)

    async def _hybrid_search(self, question: str) -> list[dict]:
        """BM25 + vector search over the full corpus, combined by fixed weights.

        final_score = 0.6 * vector_score + 0.4 * bm25_score (BM25 min-max
        normalized first, since its raw scores are unbounded).

        Returns
        -------
        list[dict]
            Up to _CANDIDATE_POOL_SIZE {"text", "score"} dicts, score-descending.
        """
        corpus_size = len(self.bm25_retriever.docs)

        bm25_raw_scores = self.bm25_retriever.vectorizer.get_scores(
            self.bm25_retriever.preprocess_func(question)
        )
        bm25_by_text = {
            doc.page_content: float(score)
            for doc, score in zip(self.bm25_retriever.docs, bm25_raw_scores)
        }
        bm25_norm = _min_max_normalize(bm25_by_text)

        vector_hits = await self.vector_store.asimilarity_search_with_relevance_scores(
            question, k=corpus_size
        )
        vector_by_text = {doc.page_content: float(score) for doc, score in vector_hits}

        combined = [
            {
                "text": text,
                "score": _VECTOR_WEIGHT * vector_by_text.get(text, 0.0)
                + _BM25_WEIGHT * bm25_norm.get(text, 0.0),
            }
            for text in bm25_by_text
        ]
        combined.sort(key=lambda d: d["score"], reverse=True)
        return combined[:_CANDIDATE_POOL_SIZE]

    async def _rerank(self, question: str, candidates: list[dict]) -> list[dict]:
        """Cross-encoder rerank of hybrid-search candidates.

        Each result's score is the cross-encoder's own relevance score,
        replacing the hybrid retrieval score — the whole point of reranking
        is that it's more accurate than the initial combination.
        """
        if not candidates:
            return candidates
        pairs = [(question, c["text"]) for c in candidates]
        scores = await asyncio.to_thread(self._cross_encoder.predict, pairs)
        reranked = [
            {"text": c["text"], "score": float(s)}
            for c, s in zip(candidates, scores)
        ]
        reranked.sort(key=lambda d: d["score"], reverse=True)
        return reranked

    async def retrieve(self, question: str) -> list[dict]:
        """Hybrid BM25+vector retrieval, reranked to the final top _FINAL_TOP_K.

        Internal seam: aquery()/acompare_query() only see the returned
        {"text", "score"} dicts and never need to know retrieval uses
        hybrid search + reranking internally.
        """
        candidates = await self._hybrid_search(question)
        reranked = await self._rerank(question, candidates)
        return reranked[:_FINAL_TOP_K]

    async def aquery(self, question: str) -> dict:
        """Answer a natural-language safety question using RAG.

        Parameters
        ----------
        question : str
            User question about city crime safety.

        Returns
        -------
        dict
            Keys: question, answer, sources, num_sources, data_citation, source_url.
        """
        results = await self.retrieve(question)
        doc_texts = [r["text"] for r in results]
        context = "\n\n".join(doc_texts)

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(
                content=f"Question: {question}\n\nRelevant data:\n{context}"
            ),
        ]

        try:
            response = await self._invoke_groq(messages)
        except _TRANSIENT_GROQ_ERRORS:
            if self.fallback_llm is None:
                raise
            response = await self.fallback_llm.ainvoke(messages)
        answer = response.content

        return {
            "question": question,
            "answer": answer,
            "sources": [t[:150] for t in doc_texts],
            "num_sources": len(doc_texts),
            "data_citation": _DATA_CITATION,
            "source_url": _SOURCE_URL,
        }

    async def acompare_query(
        self,
        city1: str,
        city2: str,
        aspect: str = "overall safety",
    ) -> dict:
        """Compare two cities on a safety aspect.

        Parameters
        ----------
        city1 : str
            First city name.
        city2 : str
            Second city name.
        aspect : str
            Safety dimension to compare (default "overall safety").

        Returns
        -------
        dict
            Same structure as aquery().
        """
        question = (
            f"Compare {city1} and {city2} in terms of {aspect}. "
            f"Which is safer and why?"
        )
        return await self.aquery(question)


# ---------------------------------------------------------------------------
# Smoke-test entry point
# ---------------------------------------------------------------------------

async def _smoke_test() -> None:
    from backend.data_loader import CrimeDataLoader

    loader = CrimeDataLoader()
    pipeline = RAGPipeline(loader.df, rebuild=True, key_findings=loader.key_findings)

    test_queries = [
        ("query", "Is Delhi City safe for women?"),
        ("query", "Which city in Maharashtra has the highest crime rate?"),
        ("compare", ("Pune", "Mumbai")),
    ]

    print("\n" + "=" * 70)
    for i, item in enumerate(test_queries, 1):
        if item[0] == "query":
            result = await pipeline.aquery(item[1])
        else:
            result = await pipeline.acompare_query(*item[1])

        print(f"\nQ{i}: {result['question']}")
        print(f"Sources used: {result['num_sources']}")
        print(f"Citation: {result['data_citation']} | {result['source_url']}")
        print(f"\nAnswer:\n{result['answer']}")
        print("=" * 70)


if __name__ == "__main__":
    sys.path.insert(0, ".")
    load_dotenv()
    asyncio.run(_smoke_test())
