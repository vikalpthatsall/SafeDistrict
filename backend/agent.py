"""
agent.py — Orchestration agent for SafeDistrict AI.

Routes natural-language queries to RAG, anomaly detection, or city
comparison using a LangGraph ReAct agent with tool calling.
"""

from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, ".")

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from rapidfuzz import fuzz, process

from backend.anomaly_engine import AnomalyEngine
from backend.config import get_settings
from backend.data_loader import CrimeDataLoader
from backend.rag_pipeline import RAGPipeline

# _handle_compare's fuzzy fallback: exact substring matching is the fast
# path; below this rapidfuzz token_sort_ratio score, a word is treated as
# too dissimilar to be that city (avoids false positives on unrelated
# question words). ~85 catches real typos (e.g. "Nagpuur" -> Nagpur, 92) but
# not historical/alternate names (e.g. "Poonah" vs "Pune" scores only 40) —
# those are handled separately, by _CITY_ALIASES below.
_FUZZY_MATCH_THRESHOLD = 85

# Historical/colonial-era and other common alternate names, checked before
# exact and fuzzy matching in _find_cities(). These aren't typos — they're
# genuinely different words from the current name (see _FUZZY_MATCH_THRESHOLD
# above), so fuzzy matching can't and shouldn't be loosened to catch them.
# Only includes names confirmed to have a distinct, real target in
# data_loader.py's city list (checked directly, not assumed) — e.g. "Bhopal"
# has no old-name alias worth adding since it was never renamed.
_CITY_ALIASES = {
    "bangalore": "Bengaluru",
    "bombay": "Mumbai",
    "poona": "Pune",
    "poonah": "Pune",
    "cochin": "Kochi",
    "calcutta": "Kolkata",
    "madras": "Chennai",
    "trivandrum": "Thiruvananthapuram",
}

_SYSTEM_PROMPT = (
    "You are SafeDistrict AI, a crime safety assistant for Indian cities. "
    "Answer the user's question by calling exactly one of these tools:\n"
    "- query_rag_tool: general safety questions, crime statistics, city overviews\n"
    "- detect_anomalies_tool: questions about crime spikes, unusual increases, outliers, "
    "or women safety\n"
    "- compare_cities_tool: questions comparing two or more cities\n"
    "Return the tool output as your final answer without modification."
)


# ---------------------------------------------------------------------------
# SafeDistrictAgent
# ---------------------------------------------------------------------------

class SafeDistrictAgent:
    """Orchestrates CrimeDataLoader, AnomalyEngine, and RAGPipeline.

    A LangGraph ReAct agent selects the correct tool based on question
    semantics and returns a structured response dict.
    """

    def __init__(self) -> None:
        self.loader = CrimeDataLoader()
        self.df = self.loader.df

        self.anomaly_engine = AnomalyEngine()
        self.anomaly_engine.fit(self.df)

        self.rag = RAGPipeline(self.df, rebuild=False, key_findings=self.loader.key_findings)

        self._last_tool_result: dict | None = None
        self._tools = self._build_tools()
        self._llm = self._build_llm()
        self._react_agent = create_react_agent(
            self._llm,
            self._tools,
            prompt=SystemMessage(content=_SYSTEM_PROMPT),
        )

    # ------------------------------------------------------------------
    # LLM factory
    # ------------------------------------------------------------------

    def _build_llm(self):
        settings = get_settings()
        if settings.anthropic_api_key:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=settings.anthropic_model, temperature=0)
        from langchain_groq import ChatGroq
        return ChatGroq(model=settings.groq_model, temperature=0)

    # ------------------------------------------------------------------
    # Tool factory
    # ------------------------------------------------------------------

    def _build_tools(self) -> list:
        agent_self = self

        @tool
        async def query_rag_tool(question: str) -> str:
            """Answer general crime safety questions using the RAG pipeline."""
            result = await agent_self._handle_rag(question)
            agent_self._last_tool_result = result
            return result["answer"]

        @tool
        async def detect_anomalies_tool(question: str) -> str:
            """Detect crime anomalies, spikes, unusual patterns, or women safety concerns in the data."""
            result = await agent_self._handle_anomaly(question)
            agent_self._last_tool_result = result
            return result["answer"]

        @tool
        async def compare_cities_tool(question: str) -> str:
            """Compare safety between two or more cities."""
            result = await agent_self._handle_compare(question)
            agent_self._last_tool_result = result
            return result["answer"]

        return [query_rag_tool, detect_anomalies_tool, compare_cities_tool]

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def arun(self, question: str) -> dict:
        """Invoke the ReAct agent and return a structured response dict.

        Returns
        -------
        dict
            Keys: question, query_type, answer, data, sources.
        """
        self._last_tool_result = None
        agent_output = await self._react_agent.ainvoke({"messages": [("human", question)]})
        final_answer = agent_output["messages"][-1].content

        if self._last_tool_result is not None:
            base = dict(self._last_tool_result)
            base["answer"] = final_answer
            return base

        return {
            "question": question,
            "query_type": "rag",
            "answer": final_answer,
            "data": {},
            "sources": [],
        }

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    async def _handle_rag(self, question: str) -> dict:
        try:
            result = await self.rag.aquery(question)
            answer = result["answer"]
            sources = result["sources"]
            num_sources = result["num_sources"]
        except Exception as exc:  # noqa: BLE001 — last-resort catch: rag_pipeline.aquery() already retries transient Groq errors (4x, 1s/2s/4s backoff) and falls back to Anthropic if configured; this only fires once both have failed, or on a non-transient error from either provider.
            answer = f"AI analysis unavailable ({exc}). Please retry later."
            sources = []
            num_sources = 0
        return {
            "question": question,
            "query_type": "rag",
            "answer": answer,
            "data": {"num_sources": num_sources},
            "sources": sources,
        }

    async def _handle_anomaly(self, question: str) -> dict:
        if "women" in question.lower():
            anomalies = self.anomaly_engine.detect_women(self.df)
            header = f"Women-safety anomaly analysis (top {min(5, len(anomalies))} cities)"
            value_label = "rape+kidnapping"
        else:
            anomalies = self.anomaly_engine.detect(self.df)
            header = f"Crime spike analysis (top {min(5, len(anomalies))} cities)"
            value_label = "crimes/lakh"
        top5 = anomalies[:5]

        lines = []
        for i, a in enumerate(top5, 1):
            severity = "SEVERE" if a.is_severe else "moderate"
            lines.append(
                f"{i}. {a.city} ({a.state}): {severity} {a.crime_type}, "
                f"{value_label}={a.actual_value:.1f}, score={a.anomaly_score:.3f}"
            )
        anomaly_summary = "\n".join(lines) if lines else "No anomalies detected."

        try:
            rag_result = await self.rag.aquery(question)
            extra = f"\n\nAdditional context:\n{rag_result['answer']}"
            sources = rag_result["sources"]
        except Exception:  # noqa: BLE001 — last-resort catch: rag_pipeline.aquery() already retries transient Groq errors (4x, 1s/2s/4s backoff) and falls back to Anthropic if configured; this only fires once both have failed, or on a non-transient error from either provider.
            extra = ""
            sources = []

        answer = f"{header}:\n{anomaly_summary}{extra}"

        return {
            "question": question,
            "query_type": "anomaly",
            "answer": answer,
            "data": [
                {
                    "city": a.city,
                    "state": a.state,
                    "crime_type": a.crime_type,
                    "anomaly_score": round(a.anomaly_score, 4),
                    "actual_value": round(a.actual_value, 2),
                    "is_severe": a.is_severe,
                }
                for a in top5
            ],
            "sources": sources,
        }

    @staticmethod
    def _find_cities(question: str, all_cities: list[str]) -> list[str]:
        """Find city names mentioned in the question.

        Checked in order: historical/alternate names (_CITY_ALIASES), then
        exact substring matching — both fast paths. Only when those together
        find fewer than 2 cities does it fall back to fuzzy matching
        (rapidfuzz token_sort_ratio, threshold _FUZZY_MATCH_THRESHOLD) of
        individual question words against the remaining city names, to catch
        typos neither of the above can.
        """
        q_lower = question.lower()
        found = []
        for alias, canonical in _CITY_ALIASES.items():
            if alias in q_lower and canonical in all_cities and canonical not in found:
                found.append(canonical)
        for city in all_cities:
            if city.lower() in q_lower and city not in found:
                found.append(city)
        if len(found) >= 2:
            return found

        remaining = [c for c in all_cities if c not in found]
        for word in question.split():
            if not remaining:
                break
            match = process.extractOne(
                word,
                remaining,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=_FUZZY_MATCH_THRESHOLD,
            )
            if match:
                city = match[0]
                found.append(city)
                remaining.remove(city)
        return found

    async def _handle_compare(self, question: str) -> dict:
        all_cities = list(self.df["city"].unique())
        found = self._find_cities(question, all_cities)

        if len(found) < 2:
            result = await self._handle_rag(question)
            result["query_type"] = "compare"
            return result

        comparison = self.anomaly_engine.compare_cities(self.df, found)

        lines = []
        for rank, profile in enumerate(comparison, 1):
            lines.append(
                f"{rank}. {profile['city']} ({profile['state']}): "
                f"safety={profile['safety_score']}/10, "
                f"risk={profile['risk_level']}, "
                f"crimes/lakh={profile['avg_crimes_per_lakh']}"
            )

        try:
            rag_result = await self.rag.acompare_query(found[0], found[1])
            extra = f"\n\nDetailed analysis:\n{rag_result['answer']}"
            sources = rag_result["sources"]
        except Exception:  # noqa: BLE001 — last-resort catch: rag_pipeline.aquery() already retries transient Groq errors (4x, 1s/2s/4s backoff) and falls back to Anthropic if configured; this only fires once both have failed, or on a non-transient error from either provider.
            extra = ""
            sources = []

        answer = (
            f"City comparison ({', '.join(found)}) — ranked safest first:\n"
            + "\n".join(lines)
            + extra
        )

        return {
            "question": question,
            "query_type": "compare",
            "answer": answer,
            "data": comparison,
            "sources": sources,
        }

    # ------------------------------------------------------------------
    # City report
    # ------------------------------------------------------------------

    async def get_city_report(self, city: str) -> dict:
        city_row = self.df[self.df["city"].str.lower() == city.lower()]
        city_data = city_row.to_dict(orient="records")[0] if not city_row.empty else {}

        safety_profile = self.anomaly_engine.get_city_safety_score(self.df, city)
        safety_score = safety_profile.get("safety_score")
        risk_level = safety_profile.get("risk_level", "—")

        anomalies = self.anomaly_engine.detect(self.df)
        is_anomaly = any(a.city.lower() == city.lower() for a in anomalies)

        try:
            rag_result = await self.rag.aquery(f"Tell me about crime safety in {city}")
            rag_summary = rag_result["answer"]
        except Exception:  # noqa: BLE001 — last-resort catch: rag_pipeline.aquery() already retries transient Groq errors (4x, 1s/2s/4s backoff) and falls back to Anthropic if configured; this only fires once both have failed, or on a non-transient error from either provider.
            rag_summary = ""

        return {
            "city_data": city_data,
            "safety_score": safety_score,
            "risk_level": risk_level,
            "is_anomaly": is_anomaly,
            "rag_summary": rag_summary,
        }


# ---------------------------------------------------------------------------
# Smoke-test entry point
# ---------------------------------------------------------------------------

async def _smoke_test() -> None:
    agent = SafeDistrictAgent()
    print("Agent ready. Testing 4 query types...")
    print("=" * 70)

    test_questions = [
        "Is Mumbai safe for families?",
        "Are there any unusual crime spikes in Delhi?",
        "Compare Pune and Nagpur for safety",
        "Which cities in Maharashtra should I avoid?",
    ]

    for i, question in enumerate(test_questions):
        if i > 0:
            await asyncio.sleep(15)  # stay within Groq free-tier TPM limit
        result = await agent.arun(question)
        print(f"\nQ: {question}")
        print(f"Query type: {result['query_type']}")
        print(f"Answer: {result['answer']}")
        print("-" * 70)

    print("\n=== City Report: Pune ===")
    report = await agent.get_city_report("Pune")
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


if __name__ == "__main__":
    asyncio.run(_smoke_test())
