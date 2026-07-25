# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SafeDistrict AI is a safety-focused AI application with a RAG (Retrieval-Augmented Generation) pipeline, an anomaly detection engine, and a conversational agent, served via a FastAPI backend and a Streamlit frontend.

## Architecture

**Backend (`backend/`)** — FastAPI app, entry point `backend/main.py`:
- `data_loader.py` — `CrimeDataLoader` loads NCRB 2023 city data via `load_crime_data()`. Crime counts are **tiered by quality** (`real` > `derived` > `estimated` > `national`), tracked per-row in a `data_quality` column — see "Data" below.
- `rag_pipeline.py` — `RAGPipeline` builds/loads a Chroma vector store (local HuggingFace `all-MiniLM-L6-v2` embeddings) from per-city documents and answers questions via `ChatGroq` (`llama-3.3-70b-versatile`). Returns `{answer, sources, data_citation, source_url}`; doesn't decide routing.
- `anomaly_engine.py` — `AnomalyEngine` (IsolationForest + StandardScaler over 7 crime features) exposes `fit`/`detect`/`detect_women`/`compare_cities`/`get_city_safety_score`/`get_state_summary`. `agent.py` only calls these methods, never sklearn directly.
- `agent.py` — `SafeDistrictAgent` wires the three above together and routes questions with a LangGraph `create_react_agent` over three tools (`query_rag_tool`, `detect_anomalies_tool`, `compare_cities_tool`). LLM choice: `ChatAnthropic(model="claude-sonnet-4-6")` if `ANTHROPIC_API_KEY` is set, else falls back to `ChatGroq(model="llama-3.3-70b-versatile")`.
- `main.py` — FastAPI app; builds one `SafeDistrictAgent` singleton in `lifespan()` and exposes it to all endpoints. Includes slowapi rate limiting (`/query` at 30/min, default 60/min) and CORS via `ALLOWED_ORIGINS`.

**Frontend** — there are **two** Streamlit entry points, not one:
- `frontend/app.py` — the actual 4-page dashboard UI; calls the backend over HTTP using `BACKEND_URL`.
- `app.py` (repo root) — Hugging Face Spaces entry point only. It `subprocess.Popen`s `uvicorn backend.main:app` in the background, polls `/health` until ready, then `exec()`s `frontend/app.py` in-process (single Spaces worker, no separate backend URL needed). Don't confuse the two when asked to "run the frontend." Live at https://huggingface.co/spaces/vikalpthatsall/SafeDistrict.

**Data**:
- `data/processed/ncrb_2023_verified.py` — hand-verified NCRB 2023 constants (exact murder/rape/kidnapping counts for a subset of cities, state-level crime ratios, national fallback ratios, key findings text). Always committed.
- `data/raw/ipc_crimes_citywise_2023.xlsx` — optional source Excel for city-wise total IPC counts (53 cities). **Gitignored** — if absent, `data_loader.py` falls back to a hardcoded 19-city dict (`_FALLBACK_TOTAL_IPC`), so a fresh clone without this file only loads 19 cities, not 53.
- `chromadb/` — persisted vector store, **gitignored**, rebuilt automatically on first run when missing (`RAGPipeline.__init__` checks `store_exists`).

**`eval/`** — regression harness, not part of the runtime app: `eval_runner.py` runs 20 golden queries (`golden_queries.py`) against a live `SafeDistrictAgent` and checks routing/grounding/hallucination; exits 1 if routing accuracy drops below 80%.

**`notebooks/`** — exploratory analysis; not part of the runtime app.

## Development Commands

All commands run from the repo root.

### Setup
```bash
python -m venv .venv
.venv\Scripts\activate   # Windows: as above; macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### Run backend
```bash
uvicorn backend.main:app --reload
# Interactive docs at http://localhost:8000/docs
```

### Run frontend (standalone dashboard, talks to backend over HTTP)
```bash
streamlit run frontend/app.py
```

### Run as a single process (mirrors the Hugging Face Spaces deployment)
```bash
streamlit run app.py
```

### Run via Docker Compose (backend + frontend as separate containers)
```bash
docker-compose up --build
```

### Run the eval/regression harness
```bash
python eval/eval_runner.py
```

### Module smoke tests
There is no pytest suite — each backend module has a `if __name__ == "__main__":` smoke test that exercises it directly against real data:
```bash
python -m backend.data_loader      # asserts known Delhi/Bengaluru counts
python -m backend.anomaly_engine   # prints top anomalies, state summary
python -m backend.rag_pipeline     # rebuilds the vector store, runs 3 sample queries
python -m backend.agent            # runs the full agent over 4 sample questions (rate-limited for Groq free tier)
```

### Environment variables
`GROQ_API_KEY` is **required** — `RAGPipeline.__init__` raises `EnvironmentError` without it, since Groq is always used for RAG generation regardless of which LLM the agent picks. `ANTHROPIC_API_KEY` is optional and only changes which model `agent.py`'s ReAct loop uses (Claude if present, else Groq Llama). `BACKEND_URL` is read by `frontend/app.py` for the API base URL. `ALLOWED_ORIGINS` (comma-separated) configures backend CORS.

## Key Conventions

- `agent.py`'s ReAct loop prefers `ChatAnthropic(model="claude-sonnet-4-6")` when `ANTHROPIC_API_KEY` is set, otherwise falls back to `ChatGroq`. `rag_pipeline.py`'s generation step always uses Groq regardless of that choice.
- RAG retrieval results feed directly into the agent's tool-use loop; keep the boundary clean — `rag_pipeline.py` returns ranked documents, `agent.py` decides how to use them.
- `anomaly_engine.py` exposes a single callable interface (`detect(df) -> list[AnomalyResult]`, plus `detect_women`/`compare_cities`/`get_city_safety_score`) so `agent.py` calls it as a tool without importing sklearn internals.

## Session Rules (read before every task)

- Work on ONE file per session only. Do not touch other files unprompted.
- Always confirm the task is complete before ending a session.
- Never install libraries not listed in requirements.txt without asking first.
- If an error repeats more than twice, stop and explain why instead of retrying.

## Tech Stack (do not deviate from this)

- Python 3.11+
- Data: pandas, numpy, scikit-learn
- AI/LLM: langchain, langchain-anthropic, anthropic
- Vector DB: chromadb
- API: fastapi, uvicorn, pydantic
- Frontend: streamlit, plotly
- Model: claude-sonnet-4-6 (never use opus unless explicitly told)
- Environment: python-dotenv for loading .env

## Project Purpose

SafeDistrict AI helps users compare crime safety across Indian districts
using NCRB data. Users ask natural language questions like "is Pune safer
than Nagpur for women?" and get data-backed answers. Target users are
people relocating within India.

## Current Build Status

- [x] Session 1: data_loader.py ✓ COMPLETE (real NCRB 2023 data, 53 cities with `data/raw/` Excel present; 19 without)
- [x] Session 2: anomaly_engine.py ✓ COMPLETE (anomaly detection, safety scores)
- [x] Session 3: rag_pipeline.py ✓ COMPLETE (ChromaDB, HuggingFace, Groq Llama)
- [x] Session 4: agent.py ✓ COMPLETE (routing, 4 query types, city reports)
- [x] Session 5: main.py ✓ COMPLETE (10 endpoints, all tested and working)
- [x] Session 6: app.py (Streamlit) ✓ COMPLETE
- [x] eval/ harness ✓ COMPLETE (20 golden queries, routing/grounding/hallucination checks)

## Data

Key columns produced by `data_loader.py`: `city`, `state`, `year`, `murder`, `rape`,
`kidnapping`, `robbery`, `burglary`, `vehicle_theft`, `total_ipc`, `population`,
`crimes_per_lakh`, plus per-field `_quality` columns and an overall `data_quality`.
See the Architecture section above for the tiered real/derived/estimated/national
sourcing and the `data/raw/` Excel fallback behavior.

## Environment Variables (.env)

```
GROQ_API_KEY=your_groq_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
BACKEND_URL=http://localhost:8000
ALLOWED_ORIGINS=http://localhost:8501
```
See "Environment variables" under Development Commands above for what each does.