from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
from fastapi.testclient import TestClient


class FakeAgent:
    """Stand-in for SafeDistrictAgent — no real data loading, no LLM, no network."""

    def __init__(self) -> None:
        self.df = pd.DataFrame(
            [
                {"city": "TestCity", "state": "TestState", "data_quality": "real", "crimes_per_lakh": 200.0},
                {"city": "OtherCity", "state": "OtherState", "data_quality": "estimated", "crimes_per_lakh": 100.0},
            ]
        )
        self.loader = SimpleNamespace(df=self.df)

        self.anomaly_engine = Mock()
        self.anomaly_engine.detect.return_value = []
        self.anomaly_engine.detect_women.return_value = []
        self.anomaly_engine.get_city_safety_score.return_value = {
            "city": "TestCity",
            "state": "TestState",
            "avg_crimes_per_lakh": 200.0,
            "women_risk_score": 0.01,
            "safety_score": 8.5,
            "risk_level": "Low",
            "anomaly_count": 0,
        }

    async def arun(self, question: str) -> dict:
        return {
            "question": question,
            "query_type": "rag",
            "answer": "fake answer",
            "data": {},
            "sources": [],
        }

    async def get_city_report(self, city: str) -> dict:
        return {
            "city_data": {"city": city},
            "safety_score": 8.5,
            "risk_level": "Low",
            "is_anomaly": False,
            "rag_summary": "fake summary",
        }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("backend.main.SafeDistrictAgent", FakeAgent)
    from backend.main import app

    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_list_cities(client: TestClient) -> None:
    response = client.get("/cities")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert {"city", "state"} <= body[0].keys()


def test_city_report_found(client: TestClient) -> None:
    response = client.get("/cities/TestCity")
    assert response.status_code == 200
    body = response.json()
    assert "safety_score" in body
    assert "risk_level" in body


def test_city_report_unknown_404(client: TestClient) -> None:
    response = client.get("/cities/NotACity")
    assert response.status_code == 404


def test_list_states(client: TestClient) -> None:
    response = client.get("/states")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert "TestState" in body


def test_anomalies(client: TestClient) -> None:
    response = client.get("/anomalies")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_top_dangerous(client: TestClient) -> None:
    response = client.get("/top-dangerous?n=2")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) <= 2
    if body:
        assert "safety_score" in body[0]
