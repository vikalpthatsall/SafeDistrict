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


# Matches conftest.py's BACKEND_API_KEY placeholder — every route except
# /health now requires this via the X-API-Key header.
AUTH_HEADERS = {"X-API-Key": "test-placeholder-api-key-not-real"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("backend.main.SafeDistrictAgent", FakeAgent)
    from backend.main import app

    # Default headers on the TestClient itself (not per-call) so every
    # existing test below keeps working unchanged.
    with TestClient(app, headers=AUTH_HEADERS) as test_client:
        yield test_client


@pytest.fixture
def bare_client(monkeypatch: pytest.MonkeyPatch):
    """Same as `client`, but with no default headers at all.

    Needed specifically for the missing-API-key test: httpx's TestClient
    merges per-call `headers=` with the client's own defaults rather than
    replacing them, and rejects `{"X-API-Key": None}` outright (verified
    directly) — so `client.get(..., headers={})` would still silently send
    the default X-API-Key and can't be used to test the no-header case.
    """
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


# ---------------------------------------------------------------------------
# /query and /compare — previously untested through the real ASGI layer.
# FakeAgent.arun already existed (Session 12) but no test ever called these
# two routes; both go through Depends(get_agent) and identical
# try/except -> HTTPException(500) handling in main.py.
# ---------------------------------------------------------------------------

def test_query_success(client: TestClient) -> None:
    response = client.post("/query", json={"question": "Is Delhi safe?"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "fake answer"
    assert body["query_type"] == "rag"


def test_query_agent_error_returns_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.main as main_module

    async def raise_error(question: str) -> dict:
        raise RuntimeError("groq is down")

    monkeypatch.setattr(main_module.agent, "arun", raise_error)

    response = client.post("/query", json={"question": "Is Delhi safe?"})

    # Session 16 scrubs raw exception text from the response — the real
    # message ("groq is down") is logged server-side, not returned to the
    # client. Confirm the leak doesn't happen and a generic message does.
    assert response.status_code == 500
    body = response.json()
    assert "groq is down" not in body["detail"]
    assert body["detail"] == "Internal server error"


# ---------------------------------------------------------------------------
# API key auth (Session 16) — every route except /health requires the
# correct X-API-Key header. /cities is representative of the other 8
# protected routes; verify_api_key doesn't vary by route.
# ---------------------------------------------------------------------------

def test_protected_route_no_api_key_returns_401(bare_client: TestClient) -> None:
    # x_api_key is optional at the FastAPI level specifically so a fully
    # missing header still reaches verify_api_key's own check and returns
    # 401 here, rather than FastAPI's own 422 for a missing required header.
    response = bare_client.get("/cities")
    assert response.status_code == 401


def test_protected_route_wrong_api_key_returns_401(client: TestClient) -> None:
    response = client.get("/cities", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


def test_protected_route_correct_api_key_succeeds(client: TestClient) -> None:
    # `client` already sends the correct key by default (see the fixture) —
    # every other test in this file is implicitly this case too, but this
    # one asserts it explicitly, matching the "correct key -> normal
    # response" case requested alongside the two 401 cases above.
    response = client.get("/cities", headers=AUTH_HEADERS)
    assert response.status_code == 200


def test_compare_success(client: TestClient) -> None:
    response = client.post(
        "/compare", json={"city1": "TestCity", "city2": "OtherCity", "aspect": "overall safety"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "fake answer"


def test_compare_agent_error_returns_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.main as main_module

    async def raise_error(question: str) -> dict:
        raise RuntimeError("groq is down")

    monkeypatch.setattr(main_module.agent, "arun", raise_error)

    response = client.post(
        "/compare", json={"city1": "TestCity", "city2": "OtherCity", "aspect": "overall safety"}
    )

    # Session 16 scrubs raw exception text from the response — the real
    # message ("groq is down") is logged server-side, not returned to the
    # client. Confirm the leak doesn't happen and a generic message does.
    assert response.status_code == 500
    body = response.json()
    assert "groq is down" not in body["detail"]
    assert body["detail"] == "Internal server error"
