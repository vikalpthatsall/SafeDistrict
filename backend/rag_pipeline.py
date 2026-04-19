"""
rag_pipeline.py — RAG pipeline for SafeDistrict AI.

Embeds NCRB 2023 city crime documents into ChromaDB using free
HuggingFace embeddings, then answers natural-language safety
queries via ChatGroq (llama-3.3-70b-versatile).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage


# ---------------------------------------------------------------------------
# Document builder
# ---------------------------------------------------------------------------

def build_crime_documents(df: pd.DataFrame) -> list[str]:
    """Convert each city row into a human-readable text document.

    Parameters
    ----------
    df : pd.DataFrame
        Enriched NCRB DataFrame from CrimeDataLoader.

    Returns
    -------
    list[str]
        One document string per city (53 total).
    """
    docs = []
    for _, row in df.iterrows():
        women_crimes = int(row["rape"]) + int(row["kidnapping"])
        doc = (
            f"In 2023, {row['city']} ({row['state']}) reported "
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
        Plain-text city documents from build_crime_documents().
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
    ) -> None:
        """Initialise the RAG pipeline.

        Parameters
        ----------
        df : pd.DataFrame
            Enriched NCRB DataFrame from CrimeDataLoader.
        rebuild : bool
            If True, delete existing store and rebuild from df.
            If False and store exists, load from disk.
        persist_dir : str
            ChromaDB persistence directory.
        """
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise EnvironmentError(
                "GROQ_API_KEY not found. Add it to your .env file:\n"
                "  GROQ_API_KEY=gsk_..."
            )

        store_exists = Path(persist_dir).exists() and any(Path(persist_dir).iterdir())

        if rebuild or not store_exists:
            print("Building vector store from NCRB documents...")
            documents = build_crime_documents(df)
            store = build_vector_store(documents, persist_dir=persist_dir)
            print(f"  {len(documents)} documents embedded -> {persist_dir}")
        else:
            print(f"Loading existing vector store from {persist_dir}")
            store = load_vector_store(persist_dir=persist_dir)

        self.retriever = store.as_retriever(search_kwargs={"k": 5})
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=groq_key,
            max_tokens=1024,
        )

    def query(self, question: str) -> dict:
        """Answer a natural-language safety question using RAG.

        Parameters
        ----------
        question : str
            User question about city crime safety.

        Returns
        -------
        dict
            Keys: question, answer, sources (list[str]), num_sources (int).
        """
        retrieved = self.retriever.invoke(question)
        doc_texts = [doc.page_content for doc in retrieved]
        context = "\n\n".join(doc_texts)

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(
                content=f"Question: {question}\n\nRelevant data:\n{context}"
            ),
        ]

        response = self.llm.invoke(messages)
        answer = response.content

        return {
            "question": question,
            "answer": answer,
            "sources": [t[:150] for t in doc_texts],
            "num_sources": len(doc_texts),
        }

    def compare_query(
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
            Same structure as query().
        """
        question = (
            f"Compare {city1} and {city2} in terms of {aspect}. "
            f"Which is safer and why?"
        )
        return self.query(question)


# ---------------------------------------------------------------------------
# Smoke-test entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.path.insert(0, ".")
    load_dotenv()

    from backend.data_loader import CrimeDataLoader

    loader = CrimeDataLoader()
    pipeline = RAGPipeline(loader.df, rebuild=True)

    test_queries = [
        ("query", "Is Delhi City safe for women?"),
        ("query", "Which city in Maharashtra has the highest crime rate?"),
        ("compare", ("Pune", "Mumbai")),
    ]

    print("\n" + "=" * 70)
    for i, item in enumerate(test_queries, 1):
        if item[0] == "query":
            result = pipeline.query(item[1])
        else:
            result = pipeline.compare_query(*item[1])

        print(f"\nQ{i}: {result['question']}")
        print(f"Sources used: {result['num_sources']}")
        print(f"\nAnswer:\n{result['answer']}")
        print("=" * 70)
