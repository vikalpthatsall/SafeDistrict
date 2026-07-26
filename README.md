---
title: SafeDistrict AI
emoji: 🏙️
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.56.0
app_file: app.py
pinned: false
---

# SafeDistrict AI 🏙️

> **AI-powered crime safety intelligence for 53 Indian cities — built on real NCRB 2023 government data.**

SafeDistrict AI lets you ask natural language questions about crime safety across Indian metropolitan cities and get data-grounded answers. Built for people making relocation decisions, it combines a RAG pipeline, anomaly detection, and a multi-page dashboard — no hallucinations, cited sources only.

---

## Live Demo

🔗 **[Live on Hugging Face Spaces](https://huggingface.co/spaces/vikalpthatsall/SafeDistrict)**  
📁 **[GitHub Repository](https://github.com/vikalpthatsall/SafeDistrict)**

---

## What it does

| Feature | Description |
|---|---|
| Natural language queries | Ask "Is Delhi safe for women?" and get answers grounded in NCRB data |
| City comparison | Compare any two cities across crime dimensions |
| Anomaly detection | Isolation Forest flags statistical outliers across 7 crime features |
| Women's safety index | Dedicated analysis of rape + kidnapping rates per lakh population |
| REST API | 10 FastAPI endpoints for programmatic access |
| Interactive dashboard | 4-page Streamlit UI with Plotly charts and dark theme |

---

## Architecture

```
User Query
    │
    ▼
Streamlit Frontend  ──►  FastAPI Backend (/query, /compare, /anomalies, /women-safety)
                              │
                    ┌─────────┴──────────┐
                    │                    │
               RAG Pipeline        Anomaly Engine
                    │                    │
          ┌─────────┴──────┐      Isolation Forest
          │                │      (StandardScaler + 7 features)
    ChromaDB          ChatGroq
    Vector Store      llama-3.3-70b
          │
    HuggingFace
    all-MiniLM-L6-v2
    (local embeddings)
          │
    NCRB 2023 Data
    (53 Indian cities)
```

**Why local embeddings?** The corpus is static (53 city documents). Using HuggingFace `all-MiniLM-L6-v2` locally eliminates per-token API costs with no quality trade-off at this scale.

**Why Isolation Forest over DBSCAN?** NCRB crime counts have extreme scale variance across cities (Delhi vs smaller metros). Isolation Forest handles this without distance-based clustering breaking down. Delhi City flagged as severe outlier (anomaly score: 1.000).

---

## Tech stack

**AI / ML**
- LangChain — agent with intelligent query routing (RAG / anomaly / comparison)
- ChromaDB — vector store with cosine similarity search (k=5 retrieval)
- HuggingFace `sentence-transformers/all-MiniLM-L6-v2` — local embeddings
- Groq API — inference on `llama-3.3-70b-versatile`
- Scikit-learn — Isolation Forest anomaly detection, StandardScaler

**Backend**
- FastAPI — 10 REST endpoints with Pydantic validation
- Pandas — NCRB data loading, enrichment, and feature engineering
- Python 3.11

**Frontend**
- Streamlit — 4-page dashboard
- Plotly — interactive charts
- Custom dark theme via CSS injection

---

## Project structure

```
SafeDistrict/
├── backend/
│   ├── data_loader.py       # CrimeDataLoader — NCRB ingestion + enrichment
│   ├── rag_pipeline.py      # RAGPipeline — embed, retrieve, generate
│   ├── anomaly_engine.py    # Isolation Forest anomaly detection
│   ├── agent.py             # LangGraph ReAct agent — routes queries to the tools above
│   └── main.py              # FastAPI app — 10 endpoints
├── frontend/
│   └── app.py               # Streamlit dashboard — 4 pages
├── eval/                    # Golden-query regression harness (routing/grounding/hallucination)
├── app.py                   # Hugging Face Spaces entry point (launches backend, then frontend)
├── requirements-prod.txt    # Minimal deployment dependencies
├── requirements.txt
└── README.md
```

---

## Quickstart

**1. Clone and install**
```bash
git clone https://github.com/vikalpthatsall/SafeDistrict.git
cd SafeDistrict
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

**2. Set up environment**
```bash
# Create .env file
echo "GROQ_API_KEY=your_groq_key_here" > .env
echo "ANTHROPIC_API_KEY=your_anthropic_key_here" >> .env
```
- `GROQ_API_KEY` is **required** — `RAGPipeline` uses `llama-3.3-70b-versatile` via Groq for answer generation regardless of what else is set. Get a free key at [console.groq.com](https://console.groq.com).
- `ANTHROPIC_API_KEY` is **optional** — if present, `agent.py` uses `claude-sonnet-4-6` for the orchestration/routing layer instead of falling back to Groq for that step. Both keys can be set at once; they drive different parts of the pipeline.
- `BACKEND_API_KEY` is **required** — a shared secret of your choosing (e.g. `openssl rand -hex 32`). Every backend route except `/health` requires it via an `X-API-Key` header; the Streamlit frontend reads this same variable and sends it automatically. Set the *same* value for both the backend and frontend processes/containers.

**3. Run the backend**
```bash
uvicorn backend.api:app --reload
# API docs at http://localhost:8000/docs
```

**4. Run the frontend**
```bash
streamlit run frontend/app.py
```

> **Note:** First run downloads ~90MB HuggingFace embedding model and builds the ChromaDB vector store. Subsequent runs load from disk.

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/query` | Natural language safety query |
| POST | `/compare` | Compare two cities |
| GET | `/anomalies` | Cities flagged as statistical outliers |
| GET | `/women-safety` | Women's safety ranking across all cities |
| GET | `/cities` | List all 53 cities in dataset |
| GET | `/city/{name}` | Full crime profile for a city |
| GET | `/rankings` | Cities ranked by crimes per lakh |
| GET | `/state/{name}` | All cities in a state |
| GET | `/health` | API health check |
| GET | `/stats` | Dataset summary statistics |

---

## Data source

**NCRB Crime in India 2023** — National Crime Records Bureau, Ministry of Home Affairs, Government of India.  
Covers 53 metropolitan cities with 100,000+ population. Features: total IPC crimes, murder, rape, kidnapping, robbery, burglary, vehicle theft, crimes per lakh population.

---

## Key design decisions

- **No OpenAI** — entire pipeline runs on free/low-cost APIs (Groq free tier + local HuggingFace)
- **Static corpus, local embeddings** — 53 documents don't justify a cloud embedding API
- **Cited sources only** — LLM instructed to answer from retrieved NCRB context, not general knowledge
- **Anomaly over ranking** — statistical outlier detection surfaces non-obvious unsafe cities that a simple ranking would miss

---

## Author

**Vikalp Kumar**  
Applied AI Engineer | [LinkedIn](https://linkedin.com/in/vikalpkumar14) | [GitHub](https://github.com/vikalpthatsall)
