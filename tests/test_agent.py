import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from backend.agent import SafeDistrictAgent
from backend.anomaly_engine import AnomalyEngine
from backend.data_loader import CrimeDataLoader

# No pytest-asyncio in requirements.txt, so tests stay plain sync `def` and
# drive the coroutines themselves via asyncio.run(), rather than adding a new
# test-only dependency just for this file.


@pytest.fixture(scope="module")
def real_df():
    return CrimeDataLoader().df


@pytest.fixture(scope="module")
def fitted_engine(real_df):
    engine = AnomalyEngine()
    engine.fit(real_df)
    return engine


@pytest.fixture
def agent(real_df, fitted_engine) -> SafeDistrictAgent:
    """SafeDistrictAgent with real df/anomaly_engine but a mocked rag (no LLM, no network)."""
    a = SafeDistrictAgent.__new__(SafeDistrictAgent)
    a.df = real_df
    a.anomaly_engine = fitted_engine
    a.rag = Mock()
    a.rag.aquery = AsyncMock(return_value={
        "question": "mocked",
        "answer": "mocked rag answer",
        "sources": [],
        "num_sources": 0,
        "data_citation": "NCRB Crime in India 2023",
        "source_url": "https://data.opencity.in/dataset/crime-in-india-2023",
    })
    a.rag.acompare_query = AsyncMock(return_value={
        "question": "mocked",
        "answer": "mocked compare answer",
        "sources": [],
        "num_sources": 0,
        "data_citation": "NCRB Crime in India 2023",
        "source_url": "https://data.opencity.in/dataset/crime-in-india-2023",
    })
    a._last_tool_result = None
    return a


def test_handle_compare_two_real_cities(agent: SafeDistrictAgent) -> None:
    result = asyncio.run(agent._handle_compare("Compare Mumbai and Pune for safety"))
    assert result["query_type"] == "compare"
    cities_in_data = {d["city"] for d in result["data"]}
    assert "Mumbai" in cities_in_data
    assert "Pune" in cities_in_data


def test_handle_compare_fuzzy_typo_resolves(agent: SafeDistrictAgent) -> None:
    # _handle_compare now falls back to rapidfuzz (token_sort_ratio, threshold
    # ~85) when exact substring matching finds fewer than 2 cities. "Nagpuur"
    # is a realistic typo (doubled letter) that exact matching can't find —
    # "nagpur" isn't a substring of "nagpuur" — but scores 92 against "Nagpur",
    # comfortably clearing the threshold, so this now resolves to a real
    # two-city comparison instead of falling back to RAG.
    result = asyncio.run(agent._handle_compare("Compare Nagpuur and Pune for safety"))
    assert result["query_type"] == "compare"
    cities_in_data = {d["city"] for d in result["data"]}
    assert "Nagpur" in cities_in_data
    assert "Pune" in cities_in_data


def test_handle_compare_alias_resolves(agent: SafeDistrictAgent) -> None:
    # "Poonah" is the old colonial-era name for Pune — not a typo (token_sort_ratio
    # scores it only 40 against "Pune", far below the fuzzy threshold; verified
    # directly), so it needed its own alias table rather than a loosened fuzzy
    # threshold. _CITY_ALIASES is checked before both exact and fuzzy matching,
    # so this now resolves to a real two-city comparison — closing the gap this
    # exact example was previously used to document as unresolved.
    result = asyncio.run(agent._handle_compare("Compare Poonah and Nagpur"))
    assert result["query_type"] == "compare"
    cities_in_data = {d["city"] for d in result["data"]}
    assert "Pune" in cities_in_data
    assert "Nagpur" in cities_in_data


def test_handle_compare_unresolvable_falls_back_to_rag(agent: SafeDistrictAgent) -> None:
    # "Zzqvwx" matches no alias, no exact substring, and no real city above
    # the fuzzy threshold (best fuzzy match against the real city list scores
    # only ~15; verified directly) — only "Nagpur" resolves, still fewer than
    # 2 cities, so this is the genuine "we truly can't find a 2nd city" case,
    # still falling back to the RAG path.
    result = asyncio.run(agent._handle_compare("Compare Zzqvwx and Nagpur"))
    assert result["query_type"] == "compare"
    assert isinstance(result["data"], dict)
    assert "num_sources" in result["data"]
    assert result["answer"] == "mocked rag answer"


def test_handle_anomaly_routes_to_women_detection(agent: SafeDistrictAgent) -> None:
    agent.anomaly_engine.detect_women = Mock(return_value=[])
    agent.anomaly_engine.detect = Mock(return_value=[])

    asyncio.run(agent._handle_anomaly("Are there any women safety concerns in Delhi?"))

    agent.anomaly_engine.detect_women.assert_called_once()
    agent.anomaly_engine.detect.assert_not_called()


def test_handle_anomaly_routes_to_general_detection(agent: SafeDistrictAgent) -> None:
    agent.anomaly_engine.detect_women = Mock(return_value=[])
    agent.anomaly_engine.detect = Mock(return_value=[])

    asyncio.run(agent._handle_anomaly("Are there any unusual crime spikes in Delhi?"))

    agent.anomaly_engine.detect.assert_called_once()
    agent.anomaly_engine.detect_women.assert_not_called()


def test_arun_returns_tool_result_shape(agent: SafeDistrictAgent) -> None:
    async def fake_ainvoke(_payload):
        agent._last_tool_result = {
            "question": "irrelevant",
            "query_type": "anomaly",
            "answer": "original answer",
            "data": [{"city": "Mumbai"}],
            "sources": [],
        }
        return {"messages": [Mock(content="final react answer")]}

    agent._react_agent = Mock()
    agent._react_agent.ainvoke = AsyncMock(side_effect=fake_ainvoke)

    result = asyncio.run(agent.arun("some question"))

    assert result["query_type"] == "anomaly"
    assert result["answer"] == "final react answer"
    assert result["data"] == [{"city": "Mumbai"}]


def test_arun_returns_default_rag_shape_when_no_tool_called(agent: SafeDistrictAgent) -> None:
    agent._react_agent = Mock()
    agent._react_agent.ainvoke = AsyncMock(
        return_value={"messages": [Mock(content="plain llm answer")]}
    )

    result = asyncio.run(agent.arun("some other question"))

    assert result == {
        "question": "some other question",
        "query_type": "rag",
        "answer": "plain llm answer",
        "data": {},
        "sources": [],
    }
