"""
rag_pipeline.py — RAG pipeline for SafeDistrict AI.

Embeds NCRB 2023 city crime documents into ChromaDB using free
HuggingFace embeddings, then answers natural-language safety
queries via ChatGroq (llama-3.3-70b-versatile).

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

    Uses ChromaDB for vector storage, HuggingFace embeddings for retrieval,
    and ChatGroq (llama-3.3-70b-versatile) for answer generation.
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
        store_exists = Path(persist_dir).exists() and any(Path(persist_dir).iterdir())

        if rebuild or not store_exists:
            print("Building vector store from NCRB documents...")
            documents = build_crime_documents(df)
            if key_findings:
                documents.append(build_key_findings_document(key_findings))
            store = build_vector_store(documents, persist_dir=persist_dir)
            print(f"  {len(documents)} documents embedded -> {persist_dir}")
        else:
            print(f"Loading existing vector store from {persist_dir}")
            store = load_vector_store(persist_dir=persist_dir)

        self.retriever = store.as_retriever(search_kwargs={"k": 5})
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
        retrieved = await self.retriever.ainvoke(question)
        doc_texts = [doc.page_content for doc in retrieved]
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
