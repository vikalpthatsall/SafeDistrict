"""
app.py — Streamlit frontend for SafeDistrict AI.

Calls backend REST API only. Never imports backend modules directly.
"""

import requests
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

BASE_URL = "http://localhost:8000"

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SafeDistrict AI",
    page_icon="🏙️",
    layout="wide",
)

# ── CSS injection — must be first after set_page_config ───────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&family=DM+Mono:wght@400;500&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"] {
  background-color: #080d1a !important;
  color: #e2e8f0 !important;
  font-family: 'DM Sans', sans-serif !important;
}

[data-testid="stSidebar"] {
  background-color: #0d1321 !important;
  border-right: 1px solid #1e2d45 !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header,
[data-testid="stToolbar"] { display: none !important; }

/* ── Main content padding ── */
.main .block-container {
  padding: 2rem 2.5rem !important;
  max-width: 1400px !important;
}

/* ── Cards ── */
.sd-card {
  background: #0f1829;
  border: 1px solid #1e2d45;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 16px;
  transition: border-color 0.2s;
}
.sd-card:hover { border-color: #2d4a6e; }

.sd-card-accent-amber { border-left: 3px solid #f59e0b !important; }
.sd-card-accent-red   { border-left: 3px solid #ef4444 !important; }
.sd-card-accent-teal  { border-left: 3px solid #14b8a6 !important; }
.sd-card-accent-blue  { border-left: 3px solid #3b82f6 !important; }

/* ── Metric cards ── */
.sd-metric {
  background: #0f1829;
  border: 1px solid #1e2d45;
  border-radius: 12px;
  padding: 20px 24px;
  text-align: center;
}
.sd-metric-value {
  font-family: 'DM Mono', monospace;
  font-size: 36px;
  font-weight: 500;
  line-height: 1;
  margin: 8px 0 4px;
}
.sd-metric-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #475569;
}
.sd-metric-amber .sd-metric-value { color: #f59e0b; }
.sd-metric-red   .sd-metric-value { color: #ef4444; }
.sd-metric-teal  .sd-metric-value { color: #14b8a6; }
.sd-metric-blue  .sd-metric-value { color: #3b82f6; }
.sd-metric-white .sd-metric-value { color: #f1f5f9; }

/* ── Section headers ── */
.sd-section-header {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #475569;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #1e2d45;
}

/* ── Page title ── */
.sd-page-title {
  font-size: 42px;
  font-weight: 300;
  line-height: 1.1;
  color: #f1f5f9;
  margin-bottom: 4px;
}
.sd-page-title span { color: #f59e0b; font-weight: 600; }

.sd-page-subtitle {
  font-size: 15px;
  color: #475569;
  margin-bottom: 32px;
  font-weight: 400;
}

/* ── Badges ── */
.badge {
  display: inline-block;
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 3px 10px;
  border-radius: 99px;
}
.badge-red    { background: #3f1010; color: #f87171; border: 1px solid #7f1d1d; }
.badge-amber  { background: #3f2a00; color: #fbbf24; border: 1px solid #78350f; }
.badge-teal   { background: #042f2e; color: #2dd4bf; border: 1px solid #134e4a; }
.badge-blue   { background: #0c1e3f; color: #60a5fa; border: 1px solid #1e3a5f; }
.badge-muted  { background: #1e2d45; color: #64748b; border: 1px solid #2d3f5e; }

/* ── Anomaly row ── */
.anomaly-row {
  background: #0f1829;
  border: 1px solid #1e2d45;
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.anomaly-city {
  font-size: 16px;
  font-weight: 500;
  color: #f1f5f9;
  flex: 1;
}
.anomaly-state {
  font-size: 13px;
  color: #475569;
}
.anomaly-score {
  font-family: 'DM Mono', monospace;
  font-size: 22px;
  font-weight: 500;
  color: #ef4444;
  min-width: 60px;
  text-align: right;
}

/* ── Progress bar ── */
.sd-progress-bg {
  background: #1e2d45;
  border-radius: 4px;
  height: 6px;
  overflow: hidden;
  flex: 1;
  min-width: 120px;
}
.sd-progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}
.sd-progress-red   { background: linear-gradient(90deg, #ef4444, #f97316); }
.sd-progress-amber { background: linear-gradient(90deg, #f59e0b, #84cc16); }

/* ── Stat table rows ── */
.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #1e2d45;
  font-size: 14px;
}
.stat-row:last-child { border-bottom: none; }
.stat-label { color: #475569; font-weight: 400; }
.stat-value {
  font-family: 'DM Mono', monospace;
  color: #f1f5f9;
  font-weight: 500;
}

/* ── Buttons ── */
.stButton > button {
  background: #0f1829 !important;
  color: #f59e0b !important;
  border: 1px solid #f59e0b !important;
  border-radius: 8px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 500 !important;
  letter-spacing: 0.03em !important;
  transition: all 0.2s !important;
}
.stButton > button:hover {
  background: #f59e0b !important;
  color: #080d1a !important;
}

/* ── Ask AI primary button ── */
.ask-btn .stButton > button {
  background: #f59e0b !important;
  color: #080d1a !important;
  width: 100% !important;
  padding: 16px !important;
  font-size: 16px !important;
  font-weight: 600 !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
  background: #0f1829 !important;
  border-color: #1e2d45 !important;
  color: #e2e8f0 !important;
  border-radius: 8px !important;
}

/* ── Text area ── */
.stTextArea textarea {
  background: #0f1829 !important;
  border-color: #1e2d45 !important;
  color: #e2e8f0 !important;
  border-radius: 8px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 15px !important;
}
.stTextArea textarea:focus {
  border-color: #f59e0b !important;
  box-shadow: 0 0 0 2px rgba(245,158,11,0.15) !important;
}

/* ── Sidebar elements ── */
[data-testid="stSidebar"] .stRadio label {
  color: #94a3b8 !important;
  font-size: 14px !important;
  font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stSidebar"] .stRadio > div {
  gap: 4px !important;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: #f59e0b !important; }

/* ── Expander ── */
.streamlit-expanderHeader {
  background: #0f1829 !important;
  border: 1px solid #1e2d45 !important;
  border-radius: 8px !important;
  color: #94a3b8 !important;
  font-family: 'DM Sans', sans-serif !important;
}

/* ── Info/success/error overrides ── */
.stAlert {
  background: #0f1829 !important;
  border-radius: 10px !important;
  border: 1px solid #1e2d45 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Chart layout template ──────────────────────────────────────────────────────

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#0a1020",
    font=dict(family="DM Sans", color="#64748b", size=12),
    margin=dict(l=10, r=60, t=40, b=10),
    height=380,
    xaxis=dict(
        gridcolor="#1e2d45",
        gridwidth=0.5,
        zeroline=False,
        tickfont=dict(size=12, color="#64748b"),
    ),
    yaxis=dict(
        gridcolor="#1e2d45",
        gridwidth=0.5,
        zeroline=False,
        tickfont=dict(size=12, color="#94a3b8"),
    ),
)

# ── Offline error card ─────────────────────────────────────────────────────────

_OFFLINE_HTML = """
<div class="sd-card sd-card-accent-red" style="text-align:center;padding:32px">
  <div style="font-size:32px;margin-bottom:12px">⚠️</div>
  <div style="font-size:18px;font-weight:600;color:#ef4444;margin-bottom:8px">
    Backend Offline
  </div>
  <div style="color:#475569;font-size:14px">
    Start with: <code style="color:#f59e0b">uvicorn backend.main:app --reload</code>
  </div>
</div>
"""


# ── API helpers ────────────────────────────────────────────────────────────────

def _get(path: str, **params):
    try:
        r = requests.get(f"{BASE_URL}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.markdown(_OFFLINE_HTML, unsafe_allow_html=True)
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def _post(path: str, payload: dict):
    try:
        r = requests.post(f"{BASE_URL}{path}", json=payload, timeout=60)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.markdown(_OFFLINE_HTML, unsafe_allow_html=True)
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


@st.cache_data(ttl=300)
def get_cities():
    return _get("/cities") or []


@st.cache_data(ttl=300)
def get_states():
    return _get("/states") or []


@st.cache_data(ttl=300)
def get_anomalies():
    return _get("/anomalies") or []


@st.cache_data(ttl=300)
def get_top_dangerous(n: int = 10):
    # Returns list of dicts with keys: city, state, avg_crimes_per_lakh,
    # women_risk_score, safety_score, risk_level, anomaly_count
    return _get("/top-dangerous", n=n) or []


@st.cache_data(ttl=300)
def get_women_safety():
    # Returns list of dicts with keys: city, state, women_risk_ratio
    return _get("/women-safety") or []


# ── Sidebar ────────────────────────────────────────────────────────────────────

st.sidebar.markdown("""
<div style="padding: 8px 0 24px">
  <div style="font-size:28px;margin-bottom:2px">🏙️</div>
  <div style="font-size:22px;font-weight:600;color:#f1f5f9;line-height:1">
    Safe<span style="color:#f59e0b">District</span>
  </div>
  <div style="font-size:11px;letter-spacing:0.15em;text-transform:uppercase;
              color:#475569;margin-top:4px">
    AI Safety Intelligence
  </div>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio(
    "",
    ["Dashboard", "City Explorer", "Compare Cities", "Ask AI"],
    label_visibility="collapsed",
)

st.sidebar.markdown("""
<div style="margin-top:24px">
  <div style="font-size:10px;font-weight:600;letter-spacing:0.1em;
              text-transform:uppercase;color:#475569;margin-bottom:12px">
    DATA & MODELS
  </div>

  <div class="sd-card" style="padding:12px 16px;margin-bottom:8px">
    <div style="font-size:13px;font-weight:500;color:#f1f5f9">NCRB 2023</div>
    <div style="font-size:11px;color:#475569;margin-top:2px">53 Metropolitan Cities</div>
  </div>

  <div class="sd-card" style="padding:12px 16px;margin-bottom:8px">
    <div style="font-size:13px;font-weight:500;color:#f1f5f9">Llama 3.3 70B</div>
    <div style="font-size:11px;color:#475569;margin-top:2px">via Groq · Free tier</div>
  </div>

  <div class="sd-card" style="padding:12px 16px">
    <div style="font-size:13px;font-weight:500;color:#f1f5f9">MiniLM-L6-v2</div>
    <div style="font-size:11px;color:#475569;margin-top:2px">HuggingFace Embeddings</div>
  </div>
</div>

<div style="margin-top:32px;font-size:11px;color:#2d3f5e;text-align:center">
  v1.0.0 · SafeDistrict AI
</div>
""", unsafe_allow_html=True)


# ── PAGE 1 — Dashboard ─────────────────────────────────────────────────────────

if page == "Dashboard":
    st.markdown("""
    <div style="margin-bottom:32px">
      <div class="sd-page-title">
        India Crime Safety <span>Explorer</span>
      </div>
      <div class="sd-page-subtitle">
        Statistical analysis of IPC crimes across 53 metropolitan cities · NCRB 2023
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Analyzing 53 cities..."):
        states = get_states()
        anomalies = get_anomalies()
        top_dangerous = get_top_dangerous(10)
        top1 = get_top_dangerous(1)
        women_safety = get_women_safety()

    most_dangerous = top1[0].get("city", "—") if top1 else "—"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class="sd-metric sd-metric-blue">
          <div class="sd-metric-label">Cities Monitored</div>
          <div class="sd-metric-value">53</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="sd-metric sd-metric-teal">
          <div class="sd-metric-label">States Covered</div>
          <div class="sd-metric-value">{len(states) if states else "—"}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="sd-metric sd-metric-red">
          <div class="sd-metric-label">Anomalies Detected</div>
          <div class="sd-metric-value">{len(anomalies) if anomalies else "—"}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="sd-metric sd-metric-amber">
          <div class="sd-metric-label">Most Dangerous City</div>
          <div class="sd-metric-value" style="font-size:24px">{most_dangerous}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    # Left — Top 10 Dangerous Cities
    with col_left:
        st.markdown('<div class="sd-section-header">TOP 10 DANGEROUS CITIES</div>',
                    unsafe_allow_html=True)
        if top_dangerous:
            df_top = pd.DataFrame(top_dangerous)
            # /top-dangerous returns get_city_safety_score profiles
            # which has avg_crimes_per_lakh (not crimes_per_lakh)
            x_col = "avg_crimes_per_lakh"
            if x_col not in df_top.columns:
                # fallback: use whichever numeric column is available
                numeric_cols = df_top.select_dtypes("number").columns.tolist()
                x_col = numeric_cols[0] if numeric_cols else None

            if x_col:
                df_top = df_top.sort_values(x_col, ascending=True)
                n = len(df_top)
                colors = [
                    f"rgb({int(239 - i * (239 - 245) / max(n - 1, 1))}, "
                    f"{int(68  + i * (158 -  68) / max(n - 1, 1))}, "
                    f"{int(68  - i * (68  -  11) / max(n - 1, 1))})"
                    for i in range(n)
                ]

                mean_val = df_top[x_col].mean()

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df_top[x_col],
                    y=df_top["city"],
                    orientation="h",
                    marker_color=colors,
                    text=df_top[x_col].round(1),
                    textposition="outside",
                    textfont=dict(color="#94a3b8", size=11),
                ))
                fig.add_vline(
                    x=mean_val,
                    line_dash="dash",
                    line_color="#475569",
                    annotation_text=f"avg {mean_val:.0f}",
                    annotation_font_color="#475569",
                    annotation_font_size=11,
                )
                layout = dict(**CHART_LAYOUT)
                layout["xaxis_title"] = None
                layout["yaxis_title"] = None
                fig.update_layout(**layout)
                st.plotly_chart(fig, use_container_width=True)

    # Right — Women Safety
    with col_right:
        st.markdown('<div class="sd-section-header">WOMEN SAFETY RISK INDEX · Crimes per Lakh Population</div>',
                    unsafe_allow_html=True)
        if women_safety:
            # /women-safety has no population or raw counts — fetch each city
            # report to get rape, kidnapping, population for per-lakh calculation
            rows = []
            for item in women_safety[:8]:
                city_name = item["city"]
                report = _get(f"/cities/{city_name}")
                if not report:
                    continue
                cd = report.get("city_data", {})
                rape = cd.get("rape", 0) or 0
                kidnap = cd.get("kidnapping", 0) or 0
                pop = cd.get("population", 0) or 0
                if pop > 0:
                    per_lakh = (rape + kidnap) / pop * 100_000
                else:
                    per_lakh = 0.0
                rows.append({"city": city_name, "women_per_lakh": per_lakh})

            if rows:
                df_women = pd.DataFrame(rows)
                # Sort descending: highest risk at top of horizontal bar chart
                df_women = df_women.sort_values("women_per_lakh", ascending=True)
                n = len(df_women)
                # Light purple = low risk (safer), dark purple = high risk
                purples = [
                    f"rgb({int(148 - i * 60 / max(n - 1, 1))}, "
                    f"{int(68  - i * 40 / max(n - 1, 1))}, "
                    f"{int(195 - i * 60 / max(n - 1, 1))})"
                    for i in range(n)
                ]
                fig2 = go.Figure(go.Bar(
                    x=df_women["women_per_lakh"],
                    y=df_women["city"],
                    orientation="h",
                    marker_color=purples,
                    text=df_women["women_per_lakh"].apply(lambda v: f"{v:.1f}"),
                    textposition="outside",
                    textfont=dict(color="#94a3b8", size=11),
                ))
                layout2 = dict(**CHART_LAYOUT)
                layout2["xaxis_title"] = None
                layout2["yaxis_title"] = None
                fig2.update_layout(**layout2)
                st.plotly_chart(fig2, use_container_width=True)

    # Anomaly section
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="sd-section-header">STATISTICAL ANOMALIES DETECTED · 2023 DATA</div>',
                unsafe_allow_html=True)

    if anomalies:
        for a in anomalies:
            is_severe = a.get("is_severe", False)
            score = float(a.get("anomaly_score", 0))
            bar_width = min(score * 100, 100)
            progress_class = "sd-progress-red" if is_severe else "sd-progress-amber"
            badge_class = "badge-red" if is_severe else "badge-amber"
            badge_label = "SEVERE" if is_severe else "MODERATE"
            icon = "🔴" if is_severe else "🟡"
            st.markdown(f"""
            <div class="anomaly-row">
              <div><span style="font-size:14px">{icon}</span></div>
              <div style="flex:1">
                <div class="anomaly-city">{a.get('city', '?')}</div>
                <div class="anomaly-state">{a.get('state', '')} · {a.get('crime_type', '')}</div>
              </div>
              <div style="flex:2">
                <div class="sd-progress-bg">
                  <div class="sd-progress-fill {progress_class}"
                       style="width:{bar_width:.0f}%"></div>
                </div>
              </div>
              <div style="text-align:right;min-width:100px">
                <div class="anomaly-score">{score:.3f}</div>
                <span class="badge {badge_class}">{badge_label}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="sd-card"><div style="color:#475569;text-align:center">No anomalies data available.</div></div>',
                    unsafe_allow_html=True)


# ── PAGE 2 — City Explorer ─────────────────────────────────────────────────────

elif page == "City Explorer":
    st.markdown("""
    <div style="margin-bottom:24px">
      <div class="sd-page-title">City <span>Explorer</span></div>
      <div class="sd-page-subtitle">Deep-dive into any city's crime profile</div>
    </div>
    """, unsafe_allow_html=True)

    cities_data = get_cities()
    if not cities_data:
        st.stop()

    city_names = sorted([c["city"] for c in cities_data])

    st.markdown('<div class="sd-section-header">SELECT CITY</div>', unsafe_allow_html=True)
    selected = st.selectbox("", city_names, label_visibility="collapsed")

    with st.spinner(f"Consulting NCRB database..."):
        report = _get(f"/cities/{selected}")

    if not report:
        st.stop()

    city_data = report.get("city_data", {})
    safety_score = float(report.get("safety_score", 0) or 0)
    is_anomaly = report.get("is_anomaly", False)
    rag_summary = report.get("rag_summary", "")

    # Safety score color
    if safety_score >= 7:
        score_class = "sd-metric-teal"
        score_color = "#14b8a6"
    elif safety_score >= 4:
        score_class = "sd-metric-amber"
        score_color = "#f59e0b"
    else:
        score_class = "sd-metric-red"
        score_color = "#ef4444"

    anomaly_badge = (
        '<span class="badge badge-red">ANOMALY</span>'
        if is_anomaly
        else '<span class="badge badge-teal">NORMAL</span>'
    )
    avg_delta = safety_score - 5.0

    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        st.markdown(f"""
        <div class="sd-metric {score_class}">
          <div class="sd-metric-label">Safety Score</div>
          <div class="sd-metric-value">{safety_score:.1f}<span style="font-size:18px;color:#475569"> / 10</span></div>
        </div>
        """, unsafe_allow_html=True)
    with mc2:
        delta_color = "#14b8a6" if avg_delta >= 0 else "#ef4444"
        delta_sign = "+" if avg_delta >= 0 else ""
        st.markdown(f"""
        <div class="sd-metric sd-metric-white">
          <div class="sd-metric-label">vs. National Average</div>
          <div class="sd-metric-value" style="color:{delta_color}">{delta_sign}{avg_delta:.1f}</div>
        </div>
        """, unsafe_allow_html=True)
    with mc3:
        st.markdown(f"""
        <div class="sd-metric sd-metric-white">
          <div class="sd-metric-label">Anomaly Status</div>
          <div class="sd-metric-value" style="font-size:20px;margin-top:16px">{anomaly_badge}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    col_chart, col_stats = st.columns(2)

    crime_keys = ["murder", "rape", "kidnapping", "robbery", "burglary", "vehicle_theft"]
    crime_colors = {
        "murder": "#ef4444",
        "rape": "#f97316",
        "kidnapping": "#f59e0b",
        "robbery": "#eab308",
        "burglary": "#3b82f6",
        "vehicle_theft": "#8b5cf6",
    }
    crime_vals = {k: city_data.get(k, 0) or 0 for k in crime_keys}

    with col_chart:
        st.markdown('<div class="sd-section-header">CRIME BREAKDOWN</div>', unsafe_allow_html=True)
        fig = go.Figure(go.Bar(
            x=list(crime_vals.keys()),
            y=list(crime_vals.values()),
            marker_color=[crime_colors[k] for k in crime_keys],
            text=[str(int(v)) for v in crime_vals.values()],
            textposition="outside",
            textfont=dict(color="#94a3b8", size=11),
        ))
        layout3 = dict(**CHART_LAYOUT)
        layout3["xaxis_title"] = None
        layout3["yaxis_title"] = None
        layout3["margin"] = dict(l=10, r=10, t=20, b=10)
        fig.update_layout(**layout3)
        st.plotly_chart(fig, use_container_width=True)

    with col_stats:
        total_ipc = city_data.get("total_ipc", city_data.get("total_cognizable_ipc", "—"))
        cpl = city_data.get("crimes_per_lakh", "—")
        population = city_data.get("population", "—")
        women_risk = int((city_data.get("rape", 0) or 0) + (city_data.get("kidnapping", 0) or 0))
        risk_level = report.get("risk_level", "—")

        total_ipc_fmt = f"{int(total_ipc):,}" if isinstance(total_ipc, (int, float)) else str(total_ipc)
        cpl_fmt = f"{cpl:.1f}" if isinstance(cpl, float) else str(cpl)
        pop_fmt = f"{int(population):,}" if isinstance(population, (int, float)) else str(population)

        st.markdown(f"""
        <div class="sd-card">
          <div class="sd-section-header">CITY STATISTICS</div>
          <div class="stat-row">
            <span class="stat-label">Total IPC Cases</span>
            <span class="stat-value">{total_ipc_fmt}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Crimes per Lakh Pop.</span>
            <span class="stat-value">{cpl_fmt}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Population</span>
            <span class="stat-value">{pop_fmt}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Women Risk Cases</span>
            <span class="stat-value">{women_risk:,}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Risk Level</span>
            <span class="stat-value" style="color:{score_color}">{risk_level}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    if rag_summary:
        st.markdown(f"""
        <div class="sd-card sd-card-accent-teal">
          <div class="sd-section-header">AI SAFETY ASSESSMENT</div>
          <div style="font-size:15px;line-height:1.8;color:#94a3b8">{rag_summary}</div>
        </div>
        """, unsafe_allow_html=True)


# ── PAGE 3 — Compare Cities ────────────────────────────────────────────────────

elif page == "Compare Cities":
    st.markdown("""
    <div style="margin-bottom:24px">
      <div class="sd-page-title">Compare <span>Cities</span></div>
      <div class="sd-page-subtitle">Side-by-side safety analysis · AI-powered verdict</div>
    </div>
    """, unsafe_allow_html=True)

    cities_data = get_cities()
    if not cities_data:
        st.stop()

    city_names = sorted([c["city"] for c in cities_data])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div style="font-size:11px;font-weight:600;letter-spacing:0.1em;
                    text-transform:uppercase;color:#3b82f6;margin-bottom:8px;
                    padding-bottom:6px;border-bottom:2px solid #3b82f6">
          CITY 1
        </div>
        """, unsafe_allow_html=True)
        city1 = st.selectbox("", city_names, index=0, key="city1_sel",
                             label_visibility="collapsed")
    with col2:
        st.markdown("""
        <div style="font-size:11px;font-weight:600;letter-spacing:0.1em;
                    text-transform:uppercase;color:#f59e0b;margin-bottom:8px;
                    padding-bottom:6px;border-bottom:2px solid #f59e0b">
          CITY 2
        </div>
        """, unsafe_allow_html=True)
        default2 = 1 if len(city_names) > 1 else 0
        city2 = st.selectbox("", city_names, index=default2, key="city2_sel",
                             label_visibility="collapsed")

    if city1 == city2:
        st.markdown("""
        <div class="sd-card sd-card-accent-amber" style="text-align:center">
          <div style="color:#f59e0b">Select two different cities to compare.</div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    if st.button("Compare →", use_container_width=False):
        with st.spinner(f"Generating AI analysis..."):
            result = _post("/compare", {"city1": city1, "city2": city2, "aspect": "overall safety"})
            r1 = _get(f"/cities/{city1}")
            r2 = _get(f"/cities/{city2}")

        if r1 and r2:
            s1 = float(r1.get("safety_score", 0) or 0)
            s2 = float(r2.get("safety_score", 0) or 0)

            # Winner banner
            if s1 > s2:
                safer_city, other_city, score_diff = city1, city2, s1 - s2
            elif s2 > s1:
                safer_city, other_city, score_diff = city2, city1, s2 - s1
            else:
                safer_city, other_city, score_diff = city1, city2, 0.0

            st.markdown(f"""
            <div class="sd-card sd-card-accent-teal" style="text-align:center;padding:32px">
              <div style="font-size:13px;color:#475569;text-transform:uppercase;
                          letter-spacing:0.1em">Safer Choice</div>
              <div style="font-size:36px;font-weight:600;color:#14b8a6;margin:8px 0">
                {safer_city}
              </div>
              <div style="color:#475569">
                {score_diff:.1f} points safer than {other_city}
              </div>
            </div>
            """, unsafe_allow_html=True)

            mc1, mc2 = st.columns(2)
            with mc1:
                score_color1 = "#14b8a6" if s1 >= 7 else ("#f59e0b" if s1 >= 4 else "#ef4444")
                st.markdown(f"""
                <div class="sd-card sd-card-accent-blue">
                  <div style="font-size:14px;font-weight:600;color:#60a5fa;
                              margin-bottom:8px">{city1}</div>
                  <div style="font-family:'DM Mono',monospace;font-size:42px;
                              font-weight:500;color:{score_color1}">{s1:.1f}</div>
                  <div style="font-size:12px;color:#475569">Safety Score / 10</div>
                </div>
                """, unsafe_allow_html=True)
            with mc2:
                score_color2 = "#14b8a6" if s2 >= 7 else ("#f59e0b" if s2 >= 4 else "#ef4444")
                st.markdown(f"""
                <div class="sd-card sd-card-accent-amber">
                  <div style="font-size:14px;font-weight:600;color:#fbbf24;
                              margin-bottom:8px">{city2}</div>
                  <div style="font-family:'DM Mono',monospace;font-size:42px;
                              font-weight:500;color:{score_color2}">{s2:.1f}</div>
                  <div style="font-size:12px;color:#475569">Safety Score / 10</div>
                </div>
                """, unsafe_allow_html=True)

            # Grouped bar chart
            d1 = r1.get("city_data", {})
            d2 = r2.get("city_data", {})
            crime_keys = ["murder", "rape", "kidnapping", "robbery", "burglary", "vehicle_theft"]
            v1 = [d1.get(k, 0) or 0 for k in crime_keys]
            v2 = [d2.get(k, 0) or 0 for k in crime_keys]

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown('<div class="sd-section-header">CRIME COMPARISON BY CATEGORY</div>',
                        unsafe_allow_html=True)

            fig_cmp = go.Figure(data=[
                go.Bar(name=city1, x=crime_keys, y=v1, marker_color="#3b82f6",
                       text=v1, textposition="outside",
                       textfont=dict(color="#94a3b8", size=10)),
                go.Bar(name=city2, x=crime_keys, y=v2, marker_color="#f59e0b",
                       text=v2, textposition="outside",
                       textfont=dict(color="#94a3b8", size=10)),
            ])
            layout_cmp = dict(**CHART_LAYOUT)
            layout_cmp["barmode"] = "group"
            layout_cmp["xaxis_title"] = None
            layout_cmp["yaxis_title"] = None
            layout_cmp["legend"] = dict(
                bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"), orientation="h",
                yanchor="bottom", y=1.02, xanchor="right", x=1,
            )
            fig_cmp.update_layout(**layout_cmp)
            st.plotly_chart(fig_cmp, use_container_width=True)

        if result:
            answer = result.get("answer", str(result))
            st.markdown(f"""
            <div class="sd-card sd-card-accent-amber">
              <div class="sd-section-header">AI COMPARATIVE ANALYSIS</div>
              <div style="font-size:15px;line-height:1.8;color:#94a3b8">{answer}</div>
            </div>
            """, unsafe_allow_html=True)


# ── PAGE 4 — Ask AI ────────────────────────────────────────────────────────────

elif page == "Ask AI":
    st.markdown("""
    <div style="margin-bottom:32px">
      <div class="sd-page-title">
        Ask <span>SafeDistrict AI</span>
      </div>
      <div class="sd-page-subtitle">
        Natural language queries · Grounded in NCRB 2023 data
      </div>
    </div>
    """, unsafe_allow_html=True)

    examples = [
        "Is Delhi safe for women?",
        "Which city in Maharashtra has the highest crime?",
        "Compare Pune and Mumbai safety",
        "Are there crime spikes anywhere in 2023?",
    ]

    if "question_input" not in st.session_state:
        st.session_state["question_input"] = ""

    st.markdown('<div class="sd-section-header">EXAMPLE QUESTIONS</div>', unsafe_allow_html=True)
    pill_cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        if pill_cols[i].button(ex, key=f"pill_{i}"):
            st.session_state["question_input"] = ex
            st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="sd-section-header">YOUR QUESTION</div>', unsafe_allow_html=True)

    question = st.text_area(
        "",
        value=st.session_state["question_input"],
        placeholder="Ask about crime safety in any Indian city…",
        height=100,
        key="qa_input",
        label_visibility="collapsed",
    )

    st.markdown('<div class="ask-btn">', unsafe_allow_html=True)
    ask_clicked = st.button(
        "Ask SafeDistrict AI →",
        use_container_width=True,
        disabled=not (question or "").strip(),
    )
    st.markdown('</div>', unsafe_allow_html=True)

    if ask_clicked and (question or "").strip():
        with st.spinner("Consulting NCRB database..."):
            result = _post("/query", {"question": question})

        if result:
            query_type = result.get("query_type", "rag").upper()
            badge_map = {
                "RAG": ("badge-blue", "CONTEXTUAL QUERY"),
                "ANOMALY": ("badge-red", "ANOMALY ANALYSIS"),
                "COMPARE": ("badge-amber", "COMPARISON"),
            }
            badge_class, badge_label = badge_map.get(query_type, ("badge-muted", query_type))
            answer = result.get("answer", "No answer returned.")

            st.markdown(f"""
            <div style="margin:16px 0 8px">
              <span class="badge {badge_class}">{badge_label}</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="sd-card sd-card-accent-blue" style="margin-top:8px">
              <div class="sd-section-header">RESPONSE</div>
              <div style="font-size:16px;line-height:1.9;color:#e2e8f0">{answer}</div>
            </div>
            """, unsafe_allow_html=True)

            sources = result.get("sources", [])
            if sources:
                with st.expander("Sources used"):
                    for src in sources:
                        st.markdown(f"""
                        <div class="sd-card" style="padding:12px 16px;margin-bottom:6px">
                          <div style="font-size:13px;color:#94a3b8">{src}</div>
                        </div>
                        """, unsafe_allow_html=True)
