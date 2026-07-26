"""
main.py — FastAPI entry point for SafeDistrict AI.

Exposes REST endpoints consumed by the Streamlit frontend.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

sys.path.insert(0, ".")

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.agent import SafeDistrictAgent
from backend.config import get_settings

# ---------------------------------------------------------------------------
# Logging — one JSON object per line. No new dependency (python-json-logger
# isn't in requirements.txt): this is a small enough formatter to write
# directly rather than add a library for it.
#
# basicConfig configures the *root* logger's handler, which every module
# logger (backend.agent, backend.rag_pipeline, etc. — each just
# logging.getLogger(__name__)) propagates to by default, so this one
# formatter covers the whole app's log output, not just main.py's own
# logger calls.
# ---------------------------------------------------------------------------

class _JSONFormatter(logging.Formatter):
    """Minimal structured formatter: timestamp, level, logger name, message."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


_json_handler = logging.StreamHandler()
_json_handler.setFormatter(_JSONFormatter())
logging.basicConfig(level=logging.INFO, handlers=[_json_handler])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiter — default 60/min; /query overrides to 30/min
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

agent: SafeDistrictAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    agent = SafeDistrictAgent()
    yield
    agent = None


def get_agent() -> SafeDistrictAgent:
    """FastAPI dependency: the ready agent, or a 503 if startup hasn't finished."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent still starting up")
    return agent


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """FastAPI dependency: the correct X-API-Key header, or a 401.

    Applied to every route except /health — uptime monitors and Docker's own
    HEALTHCHECK shouldn't need a key just to confirm the service is up.

    x_api_key is optional at the FastAPI level (not Header(...)) so a
    completely missing header still reaches this check and returns 401 —
    Header(...) (required) would make FastAPI reject a missing header with
    422 before this function ever runs, which is the wrong status code for
    an auth failure and would contradict "missing key" and "wrong key"
    behaving the same way.
    """
    if x_api_key is None or x_api_key != get_settings().backend_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SafeDistrict AI",
    description="Crime safety assistant for Indian cities powered by real NCRB 2023 data",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS — read from env; default to localhost Streamlit for local dev
# ---------------------------------------------------------------------------

_origins_raw = get_settings().allowed_origins
allowed_origins = (
    [o.strip() for o in _origins_raw.split(",") if o.strip()]
    if _origins_raw
    else ["http://localhost:8501"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Validation errors → 400
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    # Deliberately generic — method/path/status/latency only, no headers
    # (would risk logging the X-API-Key header from Session 16) and no
    # request/response body (would risk logging question/answer text, and
    # this layer has no visibility into route-internal detail like
    # query_type/num_sources/retries anyway — that's logged from inside
    # agent.py/rag_pipeline.py instead, where it's actually available).
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s — %d (%.1fms)",
        request.method, request.url.path, response.status_code, duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class CityReportRequest(BaseModel):
    city: str


class CompareRequest(BaseModel):
    city1: str
    city2: str
    aspect: str = "overall safety"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health(request: Request) -> dict:
    """Return service health, df shape, and data-quality tier breakdown."""
    if agent is None:
        return {"status": "starting", "cities_loaded": 0}
    df = agent.df
    data_quality = (
        df["data_quality"].value_counts().to_dict()
        if "data_quality" in df.columns
        else {}
    )
    return {
        "status": "ok",
        "cities_loaded": int(df["city"].nunique()),
        "df_shape": list(df.shape),
        "data_quality": data_quality,
        "message": "SafeDistrict AI is running",
    }


@app.post("/query", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def query(
    request: Request, body: QueryRequest, agent: SafeDistrictAgent = Depends(get_agent)
) -> dict:
    """Accept a natural-language question and return an agent-routed answer."""
    try:
        return await agent.arun(body.question)
    except Exception as exc:
        logger.error("Query failed: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@app.get("/cities", dependencies=[Depends(verify_api_key)])
async def list_cities(
    request: Request, agent: SafeDistrictAgent = Depends(get_agent)
) -> list[dict]:
    """Return all cities with their state, sorted alphabetically by city name."""
    df = agent.loader.df
    pairs = (
        df[["city", "state"]]
        .drop_duplicates()
        .sort_values("city")
        .to_dict(orient="records")
    )
    return pairs


@app.get("/cities/{city_name}", dependencies=[Depends(verify_api_key)])
async def city_report(
    request: Request, city_name: str, agent: SafeDistrictAgent = Depends(get_agent)
) -> dict:
    """Return a comprehensive safety report for a single city."""
    df = agent.loader.df
    match = df[df["city"].str.lower() == city_name.lower()]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"City {city_name} not found")
    try:
        return await agent.get_city_report(city_name)
    except Exception as exc:
        logger.error("City report failed for %s: %s", city_name, exc)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@app.get("/states", dependencies=[Depends(verify_api_key)])
async def list_states(
    request: Request, agent: SafeDistrictAgent = Depends(get_agent)
) -> list[str]:
    """Return all unique states in the dataset, sorted alphabetically."""
    df = agent.loader.df
    return sorted(df["state"].dropna().unique().tolist())


@app.get("/states/{state_name}/cities", dependencies=[Depends(verify_api_key)])
async def state_cities(
    request: Request, state_name: str, agent: SafeDistrictAgent = Depends(get_agent)
) -> list[dict]:
    """Return all cities in a state with their safety scores."""
    df = agent.loader.df
    state_df = df[df["state"].str.lower() == state_name.lower()]
    if state_df.empty:
        raise HTTPException(status_code=404, detail=f"State {state_name} not found")
    cities = state_df["city"].unique().tolist()
    results = []
    for city in sorted(cities):
        try:
            profile = agent.anomaly_engine.get_city_safety_score(df, city)
            results.append(profile)
        except Exception:  # noqa: BLE001, S110 — one city's safety-score failure shouldn't 500 the whole list; skip it. Real fix (log + partial-failure reporting) is roadmap Tier 2.
            pass
    return results


@app.post("/compare", dependencies=[Depends(verify_api_key)])
async def compare(
    request: Request, body: CompareRequest, agent: SafeDistrictAgent = Depends(get_agent)
) -> dict:
    """Compare two cities for a given safety aspect using the agent."""
    question = f"Compare {body.city1} and {body.city2} for {body.aspect}"
    try:
        return await agent.arun(question)
    except Exception as exc:
        logger.error("Compare failed: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@app.get("/anomalies", dependencies=[Depends(verify_api_key)])
async def anomalies(
    request: Request, agent: SafeDistrictAgent = Depends(get_agent)
) -> list[dict]:
    """Return all detected crime anomalies sorted by anomaly score descending."""
    try:
        results = agent.anomaly_engine.detect(agent.df)
        return [
            {
                "city": a.city,
                "state": a.state,
                "crime_type": a.crime_type,
                "anomaly_score": round(a.anomaly_score, 4),
                "is_severe": a.is_severe,
            }
            for a in results
        ]
    except Exception as exc:
        logger.error("Anomaly detection failed: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@app.get("/top-dangerous", dependencies=[Depends(verify_api_key)])
async def top_dangerous(
    request: Request,
    n: int = Query(default=5, ge=1, le=53),
    agent: SafeDistrictAgent = Depends(get_agent),
) -> list[dict]:
    """Return top n cities by crimes_per_lakh (most dangerous first)."""
    df = agent.loader.df
    top = (
        df[["city", "state", "crimes_per_lakh"]]
        .sort_values("crimes_per_lakh", ascending=False)
        .drop_duplicates(subset=["city"])
        .head(n)
    )
    results = []
    for _, row in top.iterrows():
        profile = agent.anomaly_engine.get_city_safety_score(df, row["city"])
        results.append(profile)
    return results


@app.get("/women-safety", dependencies=[Depends(verify_api_key)])
async def women_safety(
    request: Request, agent: SafeDistrictAgent = Depends(get_agent)
) -> list[dict]:
    """Return top cities with anomalous women-safety crime rates (rape + kidnapping)."""
    try:
        df = agent.df
        results = agent.anomaly_engine.detect_women(df)
        output = []
        for a in results:
            city_row = df[df["city"].str.lower() == a.city.lower()]
            population = float(city_row.iloc[0]["population"]) if not city_row.empty else None
            women_crimes_per_lakh = (
                round(a.actual_value / population * 100000, 2) if population else None
            )
            output.append({
                "city": a.city,
                "state": a.state,
                "year": a.year,
                "crime_type": a.crime_type,
                "actual_value": round(a.actual_value, 2),
                "women_crimes_per_lakh": women_crimes_per_lakh,
                "anomaly_score": round(a.anomaly_score, 4),
                "is_severe": a.is_severe,
            })
        return output
    except Exception as exc:
        logger.error("Women safety endpoint failed: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error") from exc
