from unittest.mock import Mock

import pytest

from backend.agent import SafeDistrictAgent
from backend.anomaly_engine import AnomalyEngine
from backend.data_loader import CrimeDataLoader


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
    a.rag.query.return_value = {
        "question": "mocked",
        "answer": "mocked rag answer",
        "sources": [],
        "num_sources": 0,
        "data_citation": "NCRB Crime in India 2023",
        "source_url": "https://data.opencity.in/dataset/crime-in-india-2023",
    }
    a.rag.compare_query.return_value = {
        "question": "mocked",
        "answer": "mocked compare answer",
        "sources": [],
        "num_sources": 0,
        "data_citation": "NCRB Crime in India 2023",
        "source_url": "https://data.opencity.in/dataset/crime-in-india-2023",
    }
    a._last_tool_result = None
    return a


def test_handle_compare_two_real_cities(agent: SafeDistrictAgent) -> None:
    result = agent._handle_compare("Compare Mumbai and Pune for safety")
    assert result["query_type"] == "compare"
    cities_in_data = {d["city"] for d in result["data"]}
    assert "Mumbai" in cities_in_data
    assert "Pune" in cities_in_data


def test_handle_compare_unrecognized_city_falls_back_to_rag(agent: SafeDistrictAgent) -> None:
    # Known limitation (roadmap Tier 3): _handle_compare finds cities via naive
    # substring matching against question text, not fuzzy/embedding matching.
    # "Poonah" (misspelled) never matches a real city, so only "Nagpur" matches —
    # fewer than 2 found cities — and this falls back to the RAG path rather
    # than raising or silently producing a one-city "comparison". Once
    # embedding-based matching lands, this test's expected behavior should
    # change to a real two-city comparison; that's the point of asserting the
    # fallback explicitly now rather than leaving it uncovered.
    result = agent._handle_compare("Compare Poonah and Nagpur")
    assert result["query_type"] == "compare"
    assert isinstance(result["data"], dict)
    assert "num_sources" in result["data"]
    assert result["answer"] == "mocked rag answer"


def test_handle_anomaly_routes_to_women_detection(agent: SafeDistrictAgent) -> None:
    agent.anomaly_engine.detect_women = Mock(return_value=[])
    agent.anomaly_engine.detect = Mock(return_value=[])

    agent._handle_anomaly("Are there any women safety concerns in Delhi?")

    agent.anomaly_engine.detect_women.assert_called_once()
    agent.anomaly_engine.detect.assert_not_called()


def test_handle_anomaly_routes_to_general_detection(agent: SafeDistrictAgent) -> None:
    agent.anomaly_engine.detect_women = Mock(return_value=[])
    agent.anomaly_engine.detect = Mock(return_value=[])

    agent._handle_anomaly("Are there any unusual crime spikes in Delhi?")

    agent.anomaly_engine.detect.assert_called_once()
    agent.anomaly_engine.detect_women.assert_not_called()


def test_run_returns_tool_result_shape(agent: SafeDistrictAgent) -> None:
    def fake_invoke(_payload):
        agent._last_tool_result = {
            "question": "irrelevant",
            "query_type": "anomaly",
            "answer": "original answer",
            "data": [{"city": "Mumbai"}],
            "sources": [],
        }
        return {"messages": [Mock(content="final react answer")]}

    agent._react_agent = Mock()
    agent._react_agent.invoke = Mock(side_effect=fake_invoke)

    result = agent.run("some question")

    assert result["query_type"] == "anomaly"
    assert result["answer"] == "final react answer"
    assert result["data"] == [{"city": "Mumbai"}]


def test_run_returns_default_rag_shape_when_no_tool_called(agent: SafeDistrictAgent) -> None:
    agent._react_agent = Mock()
    agent._react_agent.invoke = Mock(
        return_value={"messages": [Mock(content="plain llm answer")]}
    )

    result = agent.run("some other question")

    assert result == {
        "question": "some other question",
        "query_type": "rag",
        "answer": "plain llm answer",
        "data": {},
        "sources": [],
    }
