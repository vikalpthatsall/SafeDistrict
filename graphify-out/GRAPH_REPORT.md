# Graph Report - .  (2026-04-19)

## Corpus Check
- Corpus is ~3,896 words - fits in a single context window. You may not need a graph.

## Summary
- 100 nodes · 130 edges · 17 communities detected
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 24 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_SafeDistrict Architecture|SafeDistrict Architecture]]
- [[_COMMUNITY_AnomalyEngine Methods|AnomalyEngine Methods]]
- [[_COMMUNITY_Data & NCRB Layer|Data & NCRB Layer]]
- [[_COMMUNITY_DataLoader Implementation|DataLoader Implementation]]
- [[_COMMUNITY_AnomalyResult Model|AnomalyResult Model]]
- [[_COMMUNITY_CrimeDataLoader Core|CrimeDataLoader Core]]
- [[_COMMUNITY_Anomaly Detection Logic|Anomaly Detection Logic]]
- [[_COMMUNITY_Auth & API Keys|Auth & API Keys]]
- [[_COMMUNITY_Women Risk Query|Women Risk Query]]
- [[_COMMUNITY_State Data Query|State Data Query]]
- [[_COMMUNITY_Anomaly Comparison|Anomaly Comparison]]
- [[_COMMUNITY_Top Crimes Query|Top Crimes Query]]
- [[_COMMUNITY_Agent Module|Agent Module]]
- [[_COMMUNITY_FastAPI Entry Point|FastAPI Entry Point]]
- [[_COMMUNITY_RAG Pipeline Module|RAG Pipeline Module]]
- [[_COMMUNITY_Streamlit Frontend|Streamlit Frontend]]
- [[_COMMUNITY_Notebooks|Notebooks]]

## God Nodes (most connected - your core abstractions)
1. `CrimeDataLoader` - 26 edges
2. `AnomalyEngine` - 10 edges
3. `AnomalyResult` - 9 edges
4. `agent.py` - 9 edges
5. `anomaly_engine.py` - 8 edges
6. `53 Metropolitan Cities Crime Data 2023` - 7 edges
7. `Backend Layer` - 6 edges
8. `data_loader.py` - 6 edges
9. `rag_pipeline.py` - 6 edges
10. `main.py (FastAPI)` - 6 edges

## Surprising Connections (you probably didn't know these)
- `anomaly_engine.py — IsolationForest-based anomaly detection for SafeDistrict AI.` --uses--> `CrimeDataLoader`  [INFERRED]
  backend\anomaly_engine.py → backend\data_loader.py
- `Single anomalous observation returned by AnomalyEngine.detect().` --uses--> `CrimeDataLoader`  [INFERRED]
  backend\anomaly_engine.py → backend\data_loader.py
- `Derive is_severe from anomaly_score threshold.` --uses--> `CrimeDataLoader`  [INFERRED]
  backend\anomaly_engine.py → backend\data_loader.py
- `Return a readable one-line summary.` --uses--> `CrimeDataLoader`  [INFERRED]
  backend\anomaly_engine.py → backend\data_loader.py
- `Return a debug-friendly representation.` --uses--> `CrimeDataLoader`  [INFERRED]
  backend\anomaly_engine.py → backend\data_loader.py

## Hyperedges (group relationships)
- **Core AI Pipeline: RAG + Agent + Anomaly Engine** — claudemd_rag_pipeline, claudemd_agent, claudemd_anomaly_engine [EXTRACTED 0.95]
- **Backend Services Served via FastAPI** — claudemd_data_loader, claudemd_rag_pipeline, claudemd_anomaly_engine, claudemd_agent, claudemd_main [EXTRACTED 0.95]
- **NCRB Data Flow: IPC Dataset -> data_loader -> RAG Pipeline** — ipc_crimes_2023, claudemd_data_loader, claudemd_rag_pipeline [INFERRED 0.80]

## Communities

### Community 0 - "SafeDistrict Architecture"
Cohesion: 0.11
Nodes (24): agent.py, detect(df) -> list[Anomaly] Interface, anomaly_engine.py, app.py (Streamlit), Backend Layer, Build Status Tracker, ChromaDB Vector Store, claude-sonnet-4-6 Model (+16 more)

### Community 1 - "AnomalyEngine Methods"
Cohesion: 0.18
Nodes (8): AnomalyEngine, Detect anomalous cities and return sorted AnomalyResult list.          Parameter, Compute a composite safety score and risk metadata for a city.          Paramete, Return safety profiles for multiple cities, sorted safest-first.          Parame, Summarise crime statistics for all cities in a state.          Parameters, Return a debug-friendly representation of the engine state., IsolationForest-based anomaly detector over city-level crime data., Initialise the engine with an unfitted IsolationForest and scaler.          Para

### Community 2 - "Data & NCRB Layer"
Cohesion: 0.18
Nodes (13): Data Directory (data/), data_loader.py, NCRB Crime Data, pandas, CrPC 156(3) Cases Category, IPC Crimes Citywise 2023 Dataset, 53 Metropolitan Cities Crime Data 2023, Bengaluru IPC Crime Record 2023 (+5 more)

### Community 3 - "DataLoader Implementation"
Cohesion: 0.24
Nodes (8): enrich_with_crime_breakdown(), load_crime_data(), load_real_ncrb_data(), data_loader.py — Real NCRB 2023 city-level crime data loader for SafeDistrict AI, Read and clean the raw NCRB 2023 city-wise IPC crimes Excel file.      Returns, Add estimated crime-type columns, state, population, year, and rate.      Crime-, Load, enrich, and return the full NCRB 2023 city-level crime DataFrame.      Ret, Load and cache the full crime DataFrame on construction.

### Community 4 - "AnomalyResult Model"
Cohesion: 0.25
Nodes (5): AnomalyResult, Single anomalous observation returned by AnomalyEngine.detect()., Derive is_severe from anomaly_score threshold., Return a readable one-line summary., Return a debug-friendly representation.

### Community 5 - "CrimeDataLoader Core"
Cohesion: 0.25
Nodes (5): CrimeDataLoader, High-level query interface over the real NCRB 2023 city crime dataset.      Attr, Return the row(s) for the given city (case-insensitive).          Parameters, Return the number of cities in the dataset., Return a concise debug summary of the loader.

### Community 6 - "Anomaly Detection Logic"
Cohesion: 0.33
Nodes (4): detect_women_safety_anomalies(), anomaly_engine.py — IsolationForest-based anomaly detection for SafeDistrict AI., Detect cities anomalous specifically on women-safety crimes.      Fits a fresh I, Fit the scaler and IsolationForest on the provided DataFrame.          Parameter

### Community 7 - "Auth & API Keys"
Cohesion: 0.5
Nodes (4): ANTHROPIC_API_KEY, Anthropic SDK, python-dotenv, Environment Variables (.env)

### Community 8 - "Women Risk Query"
Cohesion: 1.0
Nodes (1): Return the n cities with the highest combined rape + kidnapping count.

### Community 9 - "State Data Query"
Cohesion: 1.0
Nodes (1): Return all cities in the given state (case-insensitive).          Parameters

### Community 10 - "Anomaly Comparison"
Cohesion: 1.0
Nodes (1): Enable sorted() by anomaly_score ascending.

### Community 11 - "Top Crimes Query"
Cohesion: 1.0
Nodes (1): Return the n cities with the highest crimes_per_lakh rate.          Parameters

### Community 12 - "Agent Module"
Cohesion: 1.0
Nodes (0): 

### Community 13 - "FastAPI Entry Point"
Cohesion: 1.0
Nodes (0): 

### Community 14 - "RAG Pipeline Module"
Cohesion: 1.0
Nodes (0): 

### Community 15 - "Streamlit Frontend"
Cohesion: 1.0
Nodes (0): 

### Community 16 - "Notebooks"
Cohesion: 1.0
Nodes (1): Notebooks (exploratory)

## Knowledge Gaps
- **34 isolated node(s):** `data_loader.py — Real NCRB 2023 city-level crime data loader for SafeDistrict AI`, `Read and clean the raw NCRB 2023 city-wise IPC crimes Excel file.      Returns`, `Add estimated crime-type columns, state, population, year, and rate.      Crime-`, `Load, enrich, and return the full NCRB 2023 city-level crime DataFrame.      Ret`, `High-level query interface over the real NCRB 2023 city crime dataset.      Attr` (+29 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Women Risk Query`** (2 nodes): `.get_women_risk_cities()`, `Return the n cities with the highest combined rape + kidnapping count.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `State Data Query`** (2 nodes): `.get_state()`, `Return all cities in the given state (case-insensitive).          Parameters`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Anomaly Comparison`** (2 nodes): `.__lt__()`, `Enable sorted() by anomaly_score ascending.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Top Crimes Query`** (2 nodes): `.get_top_crimes()`, `Return the n cities with the highest crimes_per_lakh rate.          Parameters`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Agent Module`** (1 nodes): `agent.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `FastAPI Entry Point`** (1 nodes): `main.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `RAG Pipeline Module`** (1 nodes): `rag_pipeline.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Streamlit Frontend`** (1 nodes): `app.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Notebooks`** (1 nodes): `Notebooks (exploratory)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CrimeDataLoader` connect `CrimeDataLoader Core` to `AnomalyEngine Methods`, `DataLoader Implementation`, `AnomalyResult Model`, `Anomaly Detection Logic`, `Women Risk Query`, `State Data Query`, `Anomaly Comparison`, `Top Crimes Query`?**
  _High betweenness centrality (0.239) - this node is a cross-community bridge._
- **Why does `data_loader.py` connect `Data & NCRB Layer` to `SafeDistrict Architecture`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Why does `agent.py` connect `SafeDistrict Architecture` to `Auth & API Keys`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `CrimeDataLoader` (e.g. with `AnomalyResult` and `AnomalyEngine`) actually correct?**
  _`CrimeDataLoader` has 17 INFERRED edges - model-reasoned connections that need verification._
- **What connects `data_loader.py — Real NCRB 2023 city-level crime data loader for SafeDistrict AI`, `Read and clean the raw NCRB 2023 city-wise IPC crimes Excel file.      Returns`, `Add estimated crime-type columns, state, population, year, and rate.      Crime-` to the rest of the system?**
  _34 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SafeDistrict Architecture` be split into smaller, more focused modules?**
  _Cohesion score 0.11 - nodes in this community are weakly interconnected._