"""
main.py — FastAPI entry point for SafeDistrict AI.

Exposes REST endpoints consumed by the Streamlit frontend.
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, ".")

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.agent import SafeDistrictAgent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
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

_origins_raw = os.getenv("ALLOWED_ORIGINS", "")
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
    response = await call_next(request)
    logger.info("%s %s — %d", request.method, request.url.path, response.status_code)
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


@app.post("/query")
@limiter.limit("30/minute")
def query(request: Request, body: QueryRequest) -> dict:
    """Accept a natural-language question and return an agent-routed answer."""
    try:
        return agent.run(body.question)
    except Exception as exc:
        logger.error("Query failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/cities")
def list_cities(request: Request) -> list[dict]:
    """Return all cities with their state, sorted alphabetically by city name."""
    df = agent.loader.df
    pairs = (
        df[["city", "state"]]
        .drop_duplicates()
        .sort_values("city")
        .to_dict(orient="records")
    )
    return pairs


@app.get("/cities/{city_name}")
def city_report(request: Request, city_name: str) -> dict:
    """Return a comprehensive safety report for a single city."""
    df = agent.loader.df
    match = df[df["city"].str.lower() == city_name.lower()]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"City {city_name} not found")
    try:
        return agent.get_city_report(city_name)
    except Exception as exc:
        logger.error("City report failed for %s: %s", city_name, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/states")
def list_states(request: Request) -> list[str]:
    """Return all unique states in the dataset, sorted alphabetically."""
    df = agent.loader.df
    return sorted(df["state"].dropna().unique().tolist())


@app.get("/states/{state_name}/cities")
def state_cities(request: Request, state_name: str) -> list[dict]:
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
        except Exception:
            pass
    return results


@app.post("/compare")
def compare(request: Request, body: CompareRequest) -> dict:
    """Compare two cities for a given safety aspect using the agent."""
    question = f"Compare {body.city1} and {body.city2} for {body.aspect}"
    try:
        return agent.run(question)
    except Exception as exc:
        logger.error("Compare failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/anomalies")
def anomalies(request: Request) -> list[dict]:
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
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/top-dangerous")
def top_dangerous(request: Request, n: int = Query(default=5, ge=1, le=53)) -> list[dict]:
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


@app.get("/women-safety")
def women_safety(request: Request) -> list[dict]:
    """Return top cities with anomalous women-safety crime rates (rape + kidnapping)."""
    try:
        results = agent.anomaly_engine.detect_women(agent.df)
        return [
            {
                "city": a.city,
                "state": a.state,
                "year": a.year,
                "crime_type": a.crime_type,
                "actual_value": round(a.actual_value, 2),
                "anomaly_score": round(a.anomaly_score, 4),
                "is_severe": a.is_severe,
            }
            for a in results
        ]
    except Exception as exc:
        logger.error("Women safety endpoint failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
