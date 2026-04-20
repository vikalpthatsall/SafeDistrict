# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SafeDistrict AI is a safety-focused AI application with a RAG (Retrieval-Augmented Generation) pipeline, an anomaly detection engine, and a conversational agent, served via a FastAPI backend and a Streamlit frontend.

## Architecture

The system has two top-level layers:

**Backend (`backend/`)** — Python services, runs as a FastAPI app (`main.py`):
- `data_loader.py` — ingests raw data from `data/` into a vector store or database
- `rag_pipeline.py` — builds/queries the RAG pipeline (embeddings, retrieval, generation)
- `anomaly_engine.py` — statistical or ML-based anomaly detection over the loaded data
- `agent.py` — Claude-powered agent that orchestrates RAG and anomaly tools to answer queries
- `main.py` — FastAPI entry point; exposes HTTP endpoints consumed by the frontend

**Frontend (`frontend/`)** — Streamlit UI (`app.py`) that calls the backend API.

**Data (`data/`)** — raw datasets consumed by `data_loader.py`.

**Notebooks (`notebooks/`)** — exploratory analysis; not part of the runtime app.

## Development Commands

All commands run from the repo root (`safedistrict-ai/`).

### Setup
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run backend
```bash
uvicorn backend.main:app --reload
```

### Run frontend
```bash
streamlit run frontend/app.py
```

### Environment variables
Copy `.env` and populate required keys (e.g. `ANTHROPIC_API_KEY`, vector DB credentials) before running either service.

## Key Conventions

- The agent in `agent.py` uses the Anthropic SDK. Use `claude-sonnet-4-6` (or newer) as the default model and enable prompt caching on system prompts where applicable.
- RAG retrieval results feed directly into the agent's tool-use loop; keep the boundary clean — `rag_pipeline.py` returns ranked documents, `agent.py` decides how to use them.
- `anomaly_engine.py` should expose a single callable interface (e.g. `detect(df) -> list[Anomaly]`) so `agent.py` can call it as a tool without importing ML internals.

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

- [x] Session 1: data_loader.py ✓ COMPLETE (real NCRB 2023 data, 53 cities)
- [x] Session 2: anomaly_engine.py ✓ COMPLETE (anomaly detection, safety scores)
- [x] Session 3: rag_pipeline.py ✓ COMPLETE (ChromaDB, HuggingFace, Groq Llama)
- [x] Session 4: agent.py ✓ COMPLETE (routing, 4 query types, city reports)
- [x] Session 5: main.py ✓ COMPLETE (10 endpoints, all tested and working)
- [ ] Session 6: app.py (Streamlit)

## Data

- Synthetic NCRB-style data generated in data_loader.py
- Real NCRB CSVs go in data/raw/ when available
- Key columns: district, state, year, murder, rape, kidnapping,
  robbery, burglary, vehicle_theft, total_cognizable_ipc, crimes_per_lakh

## Environment Variables (.env)

ANTHROPIC_API_KEY=your_key_here