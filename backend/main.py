"""
main.py — FastAPI entry point for SafeDistrict AI.

Exposes REST endpoints consumed by the Streamlit frontend.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager

sys.path.insert(0, ".")

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.agent import SafeDistrictAgent

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    response = await call_next(request)
    print(f"{request.method} {request.url.path} — {response.status_code}")
    return response


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str


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
def health() -> dict:
    """Return service health status and number of cities loaded."""
    cities_loaded = int(agent.loader.df["city"].nunique()) if agent else 0
    return {
        "status": "ok",
        "cities_loaded": cities_loaded,
        "message": "SafeDistrict AI is running",
    }


@app.post("/query")
def query(request: QueryRequest) -> dict:
    """Accept a natural-language question and return an agent-routed answer."""
    try:
        return agent.run(request.question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/cities")
def list_cities() -> list[dict]:
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
def city_report(city_name: str) -> dict:
    """Return a comprehensive safety report for a single city."""
    df = agent.loader.df
    match = df[df["city"].str.lower() == city_name.lower()]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"City {city_name} not found")
    try:
        return agent.get_city_report(city_name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/states")
def list_states() -> list[str]:
    """Return all unique states in the dataset, sorted alphabetically."""
    df = agent.loader.df
    return sorted(df["state"].dropna().unique().tolist())


@app.get("/states/{state_name}/cities")
def state_cities(state_name: str) -> list[dict]:
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
def compare(request: CompareRequest) -> dict:
    """Compare two cities for a given safety aspect using the agent."""
    question = f"Compare {request.city1} and {request.city2} for {request.aspect}"
    try:
        return agent.run(question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/anomalies")
def anomalies() -> list[dict]:
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
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/top-dangerous")
def top_dangerous(n: int = Query(default=5, ge=1, le=53)) -> list[dict]:
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
def women_safety() -> list[dict]:
    """Return top 10 cities ranked by women safety (lower ratio = safer)."""
    df = agent.loader.df.copy()
    df["women_risk_ratio"] = (df["rape"] + df["kidnapping"]) / df["total_ipc"]
    ranked = (
        df[["city", "state", "women_risk_ratio"]]
        .dropna(subset=["women_risk_ratio"])
        .drop_duplicates(subset=["city"])
        .sort_values("women_risk_ratio")
        .head(10)
    )
    return [
        {
            "city": row["city"],
            "state": row["state"],
            "women_risk_ratio": round(float(row["women_risk_ratio"]), 6),
        }
        for _, row in ranked.iterrows()
    ]
