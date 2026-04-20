"""
agent.py — Orchestration agent for SafeDistrict AI.

Routes natural-language queries to RAG, anomaly detection, or direct
city comparison based on keyword classification.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from dotenv import load_dotenv

load_dotenv()

from backend.data_loader import CrimeDataLoader
from backend.anomaly_engine import AnomalyEngine
from backend.rag_pipeline import RAGPipeline


# ---------------------------------------------------------------------------
# Query classifier
# ---------------------------------------------------------------------------

_ANOMALY_KW = {
    "spike", "anomaly", "unusual", "sudden", "increase",
    "jump", "abnormal", "outlier",
}

_COMPARE_KW = {
    "compare", "vs", "versus", "better", "safer than",
    "between", "difference", "which is safer",
}


def classify_query(question: str) -> str:
    """Classify a user question into one of three routing categories.

    Parameters
    ----------
    question : str
        Raw user question.

    Returns
    -------
    str
        One of ``"anomaly"``, ``"compare"``, or ``"rag"``.
    """
    q = question.lower()

    for kw in _ANOMALY_KW:
        if kw in q:
            return "anomaly"

    for kw in _COMPARE_KW:
        if kw in q:
            return "compare"

    return "rag"


# ---------------------------------------------------------------------------
# SafeDistrictAgent
# ---------------------------------------------------------------------------

class SafeDistrictAgent:
    """Orchestrates CrimeDataLoader, AnomalyEngine, and RAGPipeline.

    Routes each user question to the appropriate handler based on
    classify_query(), then returns a structured response dict.
    """

    def __init__(self) -> None:
        """Initialise and wire all three backend components."""
        self.loader = CrimeDataLoader()
        self.df = self.loader.df

        self.anomaly_engine = AnomalyEngine()
        self.anomaly_engine.fit(self.df)

        self.rag = RAGPipeline(self.df, rebuild=False)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, question: str) -> dict:
        """Route a question to the correct handler and return a response dict.

        Parameters
        ----------
        question : str
            User's natural-language question.

        Returns
        -------
        dict
            Keys: question, query_type, answer, data, sources.
        """
        query_type = classify_query(question)

        if query_type == "anomaly":
            return self._handle_anomaly(question)
        if query_type == "compare":
            return self._handle_compare(question)
        return self._handle_rag(question)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_rag(self, question: str) -> dict:
        """Answer a general safety question via the RAG pipeline.

        Parameters
        ----------
        question : str
            General natural-language question.

        Returns
        -------
        dict
            Keys: question, query_type, answer, data, sources.
        """
        result = self.rag.query(question)
        return {
            "question": question,
            "query_type": "rag",
            "answer": result["answer"],
            "data": {"num_sources": result["num_sources"]},
            "sources": result["sources"],
        }

    def _handle_anomaly(self, question: str) -> dict:
        """Detect crime anomalies and augment with RAG context.

        Parameters
        ----------
        question : str
            Anomaly-related question.

        Returns
        -------
        dict
            Keys: question, query_type, answer, data, sources.
        """
        anomalies = self.anomaly_engine.detect(self.df)
        top5 = anomalies[:5]

        lines = []
        for i, a in enumerate(top5, 1):
            severity = "SEVERE" if a.is_severe else "moderate"
            lines.append(
                f"{i}. {a.city} ({a.state}): {severity} anomaly, "
                f"crimes/lakh={a.actual_value:.1f}, score={a.anomaly_score:.3f}"
            )
        anomaly_summary = "\n".join(lines) if lines else "No anomalies detected."

        rag_result = self.rag.query(question)

        answer = (
            f"Crime anomaly analysis (top {len(top5)} cities):\n"
            f"{anomaly_summary}\n\n"
            f"Additional context:\n{rag_result['answer']}"
        )

        return {
            "question": question,
            "query_type": "anomaly",
            "answer": answer,
            "data": [
                {
                    "city": a.city,
                    "state": a.state,
                    "anomaly_score": round(a.anomaly_score, 4),
                    "crimes_per_lakh": round(a.actual_value, 2),
                    "is_severe": a.is_severe,
                }
                for a in top5
            ],
            "sources": rag_result["sources"],
        }

    def _handle_compare(self, question: str) -> dict:
        """Compare cities found in the question using anomaly scores and RAG.

        Parameters
        ----------
        question : str
            Comparison question naming two or more cities.

        Returns
        -------
        dict
            Keys: question, query_type, answer, data, sources.
        """
        all_cities = list(self.df["city"].unique())
        q_lower = question.lower()
        found = [c for c in all_cities if c.lower() in q_lower]

        if len(found) < 2:
            result = self._handle_rag(question)
            result["query_type"] = "compare"
            return result

        comparison = self.anomaly_engine.compare_cities(self.df, found)
        rag_result = self.rag.compare_query(found[0], found[1])

        lines = []
        for rank, profile in enumerate(comparison, 1):
            lines.append(
                f"{rank}. {profile['city']} ({profile['state']}): "
                f"safety={profile['safety_score']}/10, "
                f"risk={profile['risk_level']}, "
                f"crimes/lakh={profile['avg_crimes_per_lakh']}"
            )

        answer = (
            f"City comparison ({', '.join(found)}) — ranked safest first:\n"
            + "\n".join(lines)
            + f"\n\nDetailed analysis:\n{rag_result['answer']}"
        )

        return {
            "question": question,
            "query_type": "compare",
            "answer": answer,
            "data": comparison,
            "sources": rag_result["sources"],
        }

    # ------------------------------------------------------------------
    # City report
    # ------------------------------------------------------------------

    def get_city_report(self, city: str) -> dict:
        """Return a comprehensive safety report for a single city.

        Parameters
        ----------
        city : str
            City name (case-insensitive).

        Returns
        -------
        dict
            Keys: city_data, safety_score, is_anomaly, rag_summary.
        """
        city_row = self.df[self.df["city"].str.lower() == city.lower()]
        city_data = city_row.to_dict(orient="records")[0] if not city_row.empty else {}

        safety_profile = self.anomaly_engine.get_city_safety_score(self.df, city)
        safety_score = safety_profile.get("safety_score")

        anomalies = self.anomaly_engine.detect(self.df)
        is_anomaly = any(a.city.lower() == city.lower() for a in anomalies)

        rag_result = self.rag.query(f"Tell me about crime safety in {city}")

        return {
            "city_data": city_data,
            "safety_score": safety_score,
            "is_anomaly": is_anomaly,
            "rag_summary": rag_result["answer"],
        }


# ---------------------------------------------------------------------------
# Smoke-test entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    agent = SafeDistrictAgent()
    print("Agent ready. Testing 4 query types...")
    print("=" * 70)

    test_questions = [
        "Is Mumbai safe for families?",
        "Are there any unusual crime spikes in Delhi?",
        "Compare Pune and Nagpur for safety",
        "Which cities in Maharashtra should I avoid?",
    ]

    for question in test_questions:
        result = agent.run(question)
        print(f"\nQ: {question}")
        print(f"Query type: {result['query_type']}")
        print(f"Answer: {result['answer']}")
        print("-" * 70)

    print("\n=== City Report: Pune ===")
    report = agent.get_city_report("Pune")
    print(f"Safety score : {report['safety_score']}")
    print(f"Is anomaly   : {report['is_anomaly']}")
    print(f"RAG summary  : {report['rag_summary']}")
    if report["city_data"]:
        cd = report["city_data"]
        print(
            f"City data    : total_ipc={cd.get('total_ipc')}, "
            f"crimes_per_lakh={cd.get('crimes_per_lakh')}, "
            f"state={cd.get('state')}"
        )
