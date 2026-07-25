"""
app.py — Streamlit frontend for SafeDistrict AI.

Calls backend REST API only. Never imports backend modules directly.
"""

import os

import requests
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SafeDistrict AI",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS injection — must be first after set_page_config ───────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,300;12..96,400;12..96,500;12..96,600&family=Manrope:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Base ── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
  background-color: #0d0d10 !important;
  color: #e8e8f0 !important;
  font-family: 'Manrope', sans-serif !important;
  font-size: 14px !important;
}

/* ── Hide sidebar completely ── */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapseButton"],
#MainMenu, footer, [data-testid="stToolbar"] {
  display: none !important;
}

/* ── Main container ── */
.main .block-container {
  padding: 32px 40px 80px !important;
  max-width: 1240px !important;
}

/* ── Tabs — make them look like a top nav bar ── */
[data-testid="stTabs"] > div:first-child {
  border-bottom: 1px solid #1c1c26 !important;
  gap: 0 !important;
  padding: 0 !important;
  margin-bottom: 32px !important;
}
[data-testid="stTabs"] button[role="tab"] {
  font-family: 'Manrope', sans-serif !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  color: #8888aa !important;
  background: none !important;
  border: none !important;
  border-bottom: 2px solid transparent !important;
  padding: 14px 16px !important;
  letter-spacing: -0.01em !important;
  transition: color 0.12s !important;
}
[data-testid="stTabs"] button[role="tab"]:hover {
  color: #e8e8f0 !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
  color: #e8e8f0 !important;
  border-bottom: 2px solid #e8e8f0 !important;
  background: none !important;
}
/* Remove Streamlit's default tab underline indicator */
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
  display: none !important;
}

/* ── Page title ── */
.sd-page-title {
  font-family: 'Bricolage Grotesque', sans-serif !important;
  font-size: 30px !important;
  font-weight: 400 !important;
  letter-spacing: -0.025em !important;
  line-height: 1.1 !important;
  color: #e8e8f0 !important;
  margin-bottom: 9px !important;
}
.sd-page-meta {
  font-size: 13px !important;
  color: #8888aa !important;
  margin-bottom: 32px !important;
}

/* ── Section label ── */
.sd-label {
  font-size: 10px !important;
  font-weight: 600 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: #505068 !important;
  margin-bottom: 14px !important;
}

/* ── Panel (card) ── */
.sd-panel {
  background: #131318 !important;
  border: 1px solid #1c1c26 !important;
  border-radius: 10px !important;
  padding: 22px !important;
  margin-bottom: 18px !important;
}

/* ── Score display ── */
.sd-score {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 58px !important;
  font-weight: 500 !important;
  letter-spacing: -0.04em !important;
  line-height: 1 !important;
  margin: 4px 0 !important;
}
.sd-score-sub {
  font-size: 12px !important;
  color: #8888aa !important;
  margin-top: 7px !important;
}

/* ── City name hero ── */
.sd-city-name {
  font-family: 'Bricolage Grotesque', sans-serif !important;
  font-size: 44px !important;
  font-weight: 400 !important;
  letter-spacing: -0.03em !important;
  line-height: 1 !important;
  margin-bottom: 12px !important;
}

/* ── Tags / badges ── */
.sd-tag {
  display: inline-flex !important;
  align-items: center !important;
  font-size: 10px !important;
  font-weight: 700 !important;
  letter-spacing: 0.05em !important;
  text-transform: uppercase !important;
  padding: 3px 9px !important;
  border-radius: 3px !important;
  margin-right: 6px !important;
}
.sd-tag-hi   { background: rgba(232,64,64,0.1)  !important; color: #e84040 !important; }
.sd-tag-mod  { background: rgba(232,160,32,0.1) !important; color: #e8a020 !important; }
.sd-tag-lo   { background: rgba(32,200,160,0.1) !important; color: #20c8a0 !important; }
.sd-tag-anom { background: rgba(232,64,64,0.08)  !important; color: #e84040 !important; border: 1px solid rgba(232,64,64,0.22) !important; }
.sd-tag-ok   { background: rgba(32,200,160,0.08) !important; color: #20c8a0 !important; border: 1px solid rgba(32,200,160,0.22) !important; }

/* ── Stats table rows ── */
.sd-stat-row {
  display: flex !important;
  justify-content: space-between !important;
  align-items: center !important;
  padding: 10px 0 !important;
  border-bottom: 1px solid #1c1c26 !important;
  font-size: 13px !important;
}
.sd-stat-row:last-child { border-bottom: none !important; }
.sd-stat-k { color: #8888aa !important; }
.sd-stat-v {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 12px !important;
  color: #e8e8f0 !important;
  font-weight: 500 !important;
}

/* ── Anomaly table ── */
.sd-anomaly-row {
  display: grid !important;
  grid-template-columns: 1fr 14px 140px 70px !important;
  gap: 14px !important;
  align-items: center !important;
  padding: 12px 0 !important;
  border-bottom: 1px solid #1c1c26 !important;
}
.sd-anomaly-row:last-child { border-bottom: none !important; }
.sd-anomaly-city { font-size: 14px !important; font-weight: 500 !important; color: #e8e8f0 !important; }
.sd-anomaly-meta { font-size: 11px !important; color: #8888aa !important; margin-top: 1px !important; }
.sd-dot { width: 7px !important; height: 7px !important; border-radius: 50% !important; }
.sd-dot-sev { background: #e84040 !important; }
.sd-dot-mod { background: #e8a020 !important; }
.sd-bar-track { background: #1a1a22 !important; border-radius: 3px !important; height: 4px !important; overflow: hidden !important; }
.sd-bar-fill-sev { height: 100% !important; border-radius: 3px !important; background: #e84040 !important; }
.sd-bar-fill-mod { height: 100% !important; border-radius: 3px !important; background: #e8a020 !important; }
.sd-score-val     { font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; font-weight: 500 !important; text-align: right !important; }
.sd-score-val.sev { color: #e84040 !important; }
.sd-score-val.mod { color: #e8a020 !important; }

/* ── AI assessment block ── */
.sd-ai-block {
  background: #1a1a22 !important;
  border-radius: 6px !important;
  padding: 18px 22px !important;
  margin-top: 18px !important;
}
.sd-ai-label {
  font-size: 10px !important;
  font-weight: 600 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: #505068 !important;
  margin-bottom: 9px !important;
}
.sd-ai-text {
  font-size: 13px !important;
  line-height: 1.85 !important;
  color: #8888aa !important;
}

/* ── Verdict banner (Compare page) ── */
.sd-verdict {
  text-align: center !important;
  padding: 36px !important;
  background: #131318 !important;
  border: 1px solid #1c1c26 !important;
  border-radius: 10px !important;
  margin-bottom: 18px !important;
}
.sd-verdict-label {
  font-size: 10px !important;
  font-weight: 600 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  color: #505068 !important;
  margin-bottom: 7px !important;
}
.sd-verdict-city {
  font-family: 'Bricolage Grotesque', sans-serif !important;
  font-size: 40px !important;
  font-weight: 400 !important;
  letter-spacing: -0.025em !important;
  margin-bottom: 7px !important;
}
.sd-verdict-delta { font-size: 13px !important; color: #8888aa !important; }

/* ── Buttons ── */
.stButton > button {
  background: #e8e8f0 !important;
  color: #0d0d10 !important;
  border: none !important;
  border-radius: 6px !important;
  font-family: 'Manrope', sans-serif !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  letter-spacing: -0.01em !important;
  padding: 10px 22px !important;
  transition: opacity 0.12s !important;
}
.stButton > button:hover { opacity: 0.82 !important; background: #e8e8f0 !important; }

/* ── Select box ── */
.stSelectbox > div > div {
  background: #131318 !important;
  border-color: #252530 !important;
  color: #e8e8f0 !important;
  border-radius: 6px !important;
  font-family: 'Manrope', sans-serif !important;
}

/* ── Text area ── */
.stTextArea textarea {
  background: #131318 !important;
  border-color: #252530 !important;
  color: #e8e8f0 !important;
  border-radius: 6px !important;
  font-family: 'Manrope', sans-serif !important;
  font-size: 14px !important;
}
.stTextArea textarea:focus {
  border-color: #8888aa !important;
  box-shadow: none !important;
}
.stTextArea textarea::placeholder { color: #505068 !important; }

/* ── Plotly chart background ── */
.js-plotly-plot .plotly, .js-plotly-plot .plotly .main-svg {
  background: transparent !important;
}

/* ── Remove default Streamlit borders/shadows on expanders ── */
.streamlit-expanderHeader {
  background: #131318 !important;
  border: 1px solid #1c1c26 !important;
  border-radius: 6px !important;
  color: #8888aa !important;
  font-family: 'Manrope', sans-serif !important;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: #e8e8f0 !important; }

/* ── Chart note ── */
.sd-chart-note {
  font-size: 11px !important;
  color: #505068 !important;
  margin-top: 12px !important;
  line-height: 1.55 !important;
  padding-top: 12px !important;
  border-top: 1px solid #1c1c26 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Chart layout template ──────────────────────────────────────────────────────

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Manrope", color="#8888aa", size=12),
    margin=dict(l=10, r=60, t=20, b=10),
    height=320,
    xaxis=dict(
        gridcolor="#1c1c26", gridwidth=0.5, zeroline=False,
        tickfont=dict(size=11, color="#8888aa", family="JetBrains Mono"),
        showline=False,
    ),
    yaxis=dict(
        gridcolor="#1c1c26", gridwidth=0.5, zeroline=False,
        tickfont=dict(size=12, color="#8888aa", family="Manrope"),
        showline=False,
    ),
)

# ── Offline error card ─────────────────────────────────────────────────────────

_OFFLINE_HTML = """
<div class="sd-panel" style="text-align:center;padding:32px">
  <div style="font-size:32px;margin-bottom:12px">⚠️</div>
  <div style="font-size:18px;font-weight:600;color:#e84040;margin-bottom:8px">
    Backend Offline
  </div>
  <div style="color:#8888aa;font-size:14px">
    Start with: <code style="color:#e8e8f0">uvicorn backend.main:app --reload</code>
  </div>
</div>
"""


# ── Score color helper ─────────────────────────────────────────────────────────

def score_color(score: float) -> str:
    if score <= 4:   return "#e84040"
    elif score <= 6: return "#e8a020"
    else:            return "#20c8a0"


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
    # Returns list of dicts with keys: city, state, women_crimes_per_lakh
    return _get("/women-safety") or []


# ── Navigation ─────────────────────────────────────────────────────────────────

tab_dash, tab_city, tab_compare, tab_ask = st.tabs([
    "Dashboard", "City Explorer", "Compare", "Ask AI"
])


# ── PAGE 1 — Dashboard ─────────────────────────────────────────────────────────

with tab_dash:
    with st.spinner("Analyzing 53 cities..."):
        states = get_states()
        anomalies = get_anomalies()
        top_dangerous = get_top_dangerous(10)
        top1 = get_top_dangerous(1)
        women_safety = get_women_safety()

    most_dangerous = top1[0].get("city", "—") if top1 else "—"
    anomaly_count = len(anomalies) if anomalies else 0

    st.markdown(f"""
<div class="sd-page-title">India Crime Safety</div>
<div class="sd-page-meta">53 cities monitored · {anomaly_count} anomalies detected · NCRB 2023 · IPC crimes data</div>
""", unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<div class="sd-label">Top 10 Dangerous Cities</div>', unsafe_allow_html=True)
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
                if "state" in df_top.columns:
                    df_top["city_label"] = df_top["city"] + ", " + df_top["state"]
                else:
                    df_top["city_label"] = df_top["city"]
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
                    y=df_top["city_label"],
                    orientation="h",
                    marker_color=colors,
                    text=df_top[x_col].round(1),
                    textposition="outside",
                    textfont=dict(color="#8888aa", size=11),
                ))
                fig.add_vline(
                    x=mean_val,
                    line_dash="dash",
                    line_color="#505068",
                    annotation_text=f"avg {mean_val:.0f}",
                    annotation_font_color="#505068",
                    annotation_font_size=11,
                )
                layout = dict(**CHART_LAYOUT)
                layout["xaxis_title"] = None
                layout["yaxis_title"] = None
                fig.update_layout(**layout)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("""
<div class="sd-chart-note">
  Higher rankings reflect higher FIR reporting rates, not necessarily higher crime
  incidence. Kerala cities consistently rank high due to stronger reporting culture —
  a finding consistent with published NCRB analysis.
</div>
""", unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="sd-label">Women Safety Risk Index · Crimes per Lakh Population</div>',
                    unsafe_allow_html=True)
        if women_safety:
            rows = [
                {
                    "city": item["city"],
                    "state": item.get("state", ""),
                    "women_per_lakh": float(item.get("women_crimes_per_lakh", 0) or 0),
                }
                for item in women_safety[:8]
            ]

            if rows:
                df_women = pd.DataFrame(rows)
                # Sort descending: highest risk at top of horizontal bar chart
                df_women = df_women.sort_values("women_per_lakh", ascending=True)
                if "state" in df_women.columns:
                    df_women["city_label"] = df_women["city"] + ", " + df_women["state"]
                else:
                    df_women["city_label"] = df_women["city"]
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
                    y=df_women["city_label"],
                    orientation="h",
                    marker_color=purples,
                    text=df_women["women_per_lakh"].apply(lambda v: f"{v:.1f}"),
                    textposition="outside",
                    textfont=dict(color="#8888aa", size=11),
                ))
                layout2 = dict(**CHART_LAYOUT)
                layout2["xaxis_title"] = None
                layout2["yaxis_title"] = None
                fig2.update_layout(**layout2)
                st.plotly_chart(fig2, use_container_width=True)
                st.markdown("""
<div class="sd-chart-note">
  Higher rankings reflect higher FIR reporting rates, not necessarily higher crime
  incidence. Kerala cities consistently rank high due to stronger reporting culture —
  a finding consistent with published NCRB analysis.
</div>
""", unsafe_allow_html=True)

    # Anomaly section — all rows in a single panel
    if anomalies:
        anomaly_rows_html = ""
        for a in anomalies:
            is_sev = a.get("is_severe", False)
            score  = float(a.get("anomaly_score", 0))
            bar_w  = min(int(score * 100), 100)
            dot_c  = "sd-dot-sev" if is_sev else "sd-dot-mod"
            bar_c  = "sd-bar-fill-sev" if is_sev else "sd-bar-fill-mod"
            score_c = "sev" if is_sev else "mod"
            anomaly_rows_html += f"""
  <div class="sd-anomaly-row">
    <div>
      <div class="sd-anomaly-city">{a.get('city', '?')}</div>
      <div class="sd-anomaly-meta">{a.get('state', '')} · {a.get('crime_type', '')}</div>
    </div>
    <div class="sd-dot {dot_c}"></div>
    <div class="sd-bar-track">
      <div class="{bar_c}" style="width:{bar_w}%"></div>
    </div>
    <div class="sd-score-val {score_c}">{score:.3f}</div>
  </div>"""

        st.markdown(f"""
<div class="sd-panel">
  <div class="sd-label">Unusual Crime Patterns · 2023 Data</div>
  {anomaly_rows_html}
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown("""
<div class="sd-panel">
  <div style="color:#8888aa;text-align:center">No crime spike data available.</div>
</div>
""", unsafe_allow_html=True)


# ── PAGE 2 — City Explorer ─────────────────────────────────────────────────────

with tab_city:
    st.markdown("""
<div class="sd-page-title">City Explorer</div>
<div class="sd-page-meta">Deep-dive into any city's crime profile</div>
""", unsafe_allow_html=True)

    cities_data = get_cities()
    if not cities_data:
        st.warning("Could not load city data. Is the backend running?")
    else:
        city_options = sorted(cities_data, key=lambda c: c["city"])
        display_names = [f"{c['city']} ({c.get('state', '')})" for c in city_options]
        city_for_display = {f"{c['city']} ({c.get('state', '')})": c["city"] for c in city_options}

        selected_display = st.selectbox("", display_names, label_visibility="collapsed")
        selected = city_for_display[selected_display]

        with st.spinner("Consulting NCRB database..."):
            report = _get(f"/cities/{selected}")

        if not report:
            st.warning("Could not load city report.")
        else:
            city_data = report.get("city_data", {})
            safety_score_val = float(report.get("safety_score", 0) or 0)
            is_anomaly = report.get("is_anomaly", False)
            rag_summary = report.get("rag_summary", "")
            risk_level = report.get("risk_level", "—")
            state = city_data.get("state", "")

            risk_class_map = {"Low": "lo", "Moderate": "mod", "High": "hi"}
            risk_class = risk_class_map.get(risk_level, "mod")

            sc = score_color(safety_score_val)
            avg_delta = safety_score_val - 5.0
            delta_color = "#20c8a0" if avg_delta >= 0 else "#e84040"
            delta_sign = "+" if avg_delta >= 0 else ""

            st.markdown(f"""
<div class="sd-city-name">{selected}</div>
<div style="display:flex;align-items:center;gap:8px;margin-bottom:28px">
  <span style="font-size:13px;color:#8888aa">{state}</span>
  <span class="sd-tag sd-tag-{risk_class}">{risk_level} Risk</span>
  <span class="sd-tag {'sd-tag-anom' if is_anomaly else 'sd-tag-ok'}">
    {'Anomaly detected' if is_anomaly else 'No anomaly'}
  </span>
</div>
""", unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
<div class="sd-panel">
  <div class="sd-label">Safety Score</div>
  <div class="sd-score" style="color:{sc}">{safety_score_val:.1f}</div>
  <div class="sd-score-sub">out of 10 · higher is safer</div>
</div>
""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
<div class="sd-panel">
  <div class="sd-label">vs. National Average</div>
  <div class="sd-score" style="color:{delta_color}">{delta_sign}{avg_delta:.1f}</div>
  <div class="sd-score-sub">relative to 5.0 average score</div>
</div>
""", unsafe_allow_html=True)

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
                st.markdown('<div class="sd-label">Crime Breakdown</div>', unsafe_allow_html=True)
                fig = go.Figure(go.Bar(
                    x=list(crime_vals.keys()),
                    y=list(crime_vals.values()),
                    marker_color=[crime_colors[k] for k in crime_keys],
                    text=[str(int(v)) for v in crime_vals.values()],
                    textposition="outside",
                    textfont=dict(color="#8888aa", size=11),
                ))
                layout3 = dict(**CHART_LAYOUT)
                layout3["title"] = dict(
                    text=f"Crime Breakdown — {selected}, 2023",
                    font=dict(size=13, color="#8888aa"),
                    x=0,
                )
                layout3["xaxis_title"] = None
                layout3["yaxis_title"] = "Reported Cases"
                layout3["margin"] = dict(l=10, r=10, t=50, b=10)
                fig.update_layout(**layout3)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("""
<div class="sd-chart-note">
  Reported IPC cases by crime category · Source: NCRB 2023
</div>
""", unsafe_allow_html=True)

            with col_stats:
                total_ipc = city_data.get("total_ipc", city_data.get("total_cognizable_ipc", "—"))
                cpl = city_data.get("crimes_per_lakh", "—")
                population = city_data.get("population", "—")
                women_risk = int((city_data.get("rape", 0) or 0) + (city_data.get("kidnapping", 0) or 0))

                total_ipc_fmt = f"{int(total_ipc):,}" if isinstance(total_ipc, (int, float)) else str(total_ipc)
                cpl_fmt = f"{cpl:.1f}" if isinstance(cpl, float) else str(cpl)
                pop_fmt = f"{int(population):,}" if isinstance(population, (int, float)) else str(population)

                st.markdown(f"""
<div class="sd-panel">
  <div class="sd-label">City Statistics</div>
  <div class="sd-stat-row"><span class="sd-stat-k">Total IPC Cases</span><span class="sd-stat-v">{total_ipc_fmt}</span></div>
  <div class="sd-stat-row"><span class="sd-stat-k">Crimes per Lakh</span><span class="sd-stat-v">{cpl_fmt}</span></div>
  <div class="sd-stat-row"><span class="sd-stat-k">Population</span><span class="sd-stat-v">{pop_fmt}</span></div>
  <div class="sd-stat-row"><span class="sd-stat-k">Women Risk Cases</span><span class="sd-stat-v">{women_risk:,}</span></div>
  <div class="sd-stat-row"><span class="sd-stat-k">Risk Level</span><span class="sd-stat-v" style="color:{sc}">{risk_level}</span></div>
</div>
""", unsafe_allow_html=True)

            if rag_summary:
                st.markdown(f"""
<div class="sd-ai-block">
  <div class="sd-ai-label">AI Safety Assessment</div>
  <div class="sd-ai-text">{rag_summary}</div>
</div>
""", unsafe_allow_html=True)


# ── PAGE 3 — Compare Cities ────────────────────────────────────────────────────

with tab_compare:
    st.markdown("""
<div class="sd-page-title">Compare Cities</div>
<div class="sd-page-meta">Side-by-side safety analysis · AI-powered verdict</div>
""", unsafe_allow_html=True)

    cities_data = get_cities()
    if not cities_data:
        st.warning("Could not load city data. Is the backend running?")
    else:
        city_options_c = sorted(cities_data, key=lambda c: c["city"])
        display_names_c = [f"{c['city']} ({c.get('state', '')})" for c in city_options_c]
        city_for_display_c = {f"{c['city']} ({c.get('state', '')})": c["city"] for c in city_options_c}

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="sd-label">City 1</div>', unsafe_allow_html=True)
            city1_display = st.selectbox("", display_names_c, index=0, key="city1_sel",
                                 label_visibility="collapsed")
            city1 = city_for_display_c[city1_display]
        with col2:
            st.markdown('<div class="sd-label">City 2</div>', unsafe_allow_html=True)
            default2 = 1 if len(display_names_c) > 1 else 0
            city2_display = st.selectbox("", display_names_c, index=default2, key="city2_sel",
                                 label_visibility="collapsed")
            city2 = city_for_display_c[city2_display]

        if city1 == city2:
            st.markdown("""
<div class="sd-panel" style="text-align:center">
  <div style="color:#e8a020">Select two different cities to compare.</div>
</div>
""", unsafe_allow_html=True)
        else:
            if st.button("Compare →", use_container_width=False):
                with st.spinner("Generating AI analysis..."):
                    result = _post("/compare", {"city1": city1, "city2": city2, "aspect": "overall safety"})
                    r1 = _get(f"/cities/{city1}")
                    r2 = _get(f"/cities/{city2}")

                if r1 and r2:
                    s1 = float(r1.get("safety_score", 0) or 0)
                    s2 = float(r2.get("safety_score", 0) or 0)
                    state1 = r1.get("city_data", {}).get("state", "")
                    state2 = r2.get("city_data", {}).get("state", "")

                    if s1 > s2:
                        safer_city, other_city, score_diff = city1, city2, s1 - s2
                    elif s2 > s1:
                        safer_city, other_city, score_diff = city2, city1, s2 - s1
                    else:
                        safer_city, other_city, score_diff = city1, city2, 0.0

                    st.markdown(f"""
<div class="sd-verdict">
  <div class="sd-verdict-label">Safer Choice</div>
  <div class="sd-verdict-city">{safer_city}</div>
  <div class="sd-verdict-delta">{score_diff:.1f} points safer than {other_city}</div>
</div>
""", unsafe_allow_html=True)

                    mc1, mc2 = st.columns(2)
                    with mc1:
                        s1_color = score_color(s1)
                        st.markdown(f"""
<div class="sd-panel">
  <div class="sd-label">{city1} · {state1}</div>
  <div class="sd-score" style="color:{s1_color}">{s1:.1f}</div>
  <div class="sd-score-sub">Safety Score / 10</div>
</div>
""", unsafe_allow_html=True)
                    with mc2:
                        s2_color = score_color(s2)
                        st.markdown(f"""
<div class="sd-panel">
  <div class="sd-label">{city2} · {state2}</div>
  <div class="sd-score" style="color:{s2_color}">{s2:.1f}</div>
  <div class="sd-score-sub">Safety Score / 10</div>
</div>
""", unsafe_allow_html=True)

                    st.markdown("""
<div class="sd-ai-block" style="margin-top:0">
  <div class="sd-ai-label">How the Safety Score is Calculated</div>
  <div class="sd-ai-text">
    The safety score (0–10) is calculated from three factors:
    <strong style="color:#e8e8f0">crimes per lakh population</strong> (how the city
    compares to the national average), <strong style="color:#e8e8f0">crime type
    distribution</strong> (weighting violent crimes higher), and
    <strong style="color:#e8e8f0">statistical deviation</strong> from similar-sized
    cities. A score of 10 means the safest possible city in the dataset.
    Source: NCRB 2023.
  </div>
</div>
""", unsafe_allow_html=True)

                    # Grouped bar chart
                    d1 = r1.get("city_data", {})
                    d2 = r2.get("city_data", {})
                    crime_keys = ["murder", "rape", "kidnapping", "robbery", "burglary", "vehicle_theft"]
                    v1 = [d1.get(k, 0) or 0 for k in crime_keys]
                    v2 = [d2.get(k, 0) or 0 for k in crime_keys]

                    st.markdown('<div class="sd-label" style="margin-top:24px">Crime Comparison by Category</div>',
                                unsafe_allow_html=True)

                    fig_cmp = go.Figure(data=[
                        go.Bar(name=city1, x=crime_keys, y=v1, marker_color="#3b82f6",
                               text=v1, textposition="outside",
                               textfont=dict(color="#8888aa", size=10)),
                        go.Bar(name=city2, x=crime_keys, y=v2, marker_color="#f59e0b",
                               text=v2, textposition="outside",
                               textfont=dict(color="#8888aa", size=10)),
                    ])
                    layout_cmp = dict(**CHART_LAYOUT)
                    layout_cmp["barmode"] = "group"
                    layout_cmp["xaxis_title"] = None
                    layout_cmp["yaxis_title"] = None
                    layout_cmp["legend"] = dict(
                        bgcolor="rgba(0,0,0,0)", font=dict(color="#8888aa"), orientation="h",
                        yanchor="bottom", y=1.02, xanchor="right", x=1,
                    )
                    fig_cmp.update_layout(**layout_cmp)
                    st.plotly_chart(fig_cmp, use_container_width=True)

                if result:
                    answer = result.get("answer", str(result))
                    st.markdown(f"""
<div class="sd-ai-block" style="margin-top:0">
  <div class="sd-ai-label">AI Comparative Analysis</div>
  <div class="sd-ai-text">{answer}</div>
</div>
""", unsafe_allow_html=True)


# ── PAGE 4 — Ask AI ────────────────────────────────────────────────────────────

with tab_ask:
    st.markdown("""
<div class="sd-page-title">Ask SafeDistrict AI</div>
<div class="sd-page-meta">Natural language queries · Grounded in NCRB 2023 data</div>
""", unsafe_allow_html=True)

    examples = [
        "Is Delhi safe for women?",
        "Which city in Maharashtra has the highest crime?",
        "Compare Pune and Mumbai safety",
        "Are there crime spikes anywhere in 2023?",
    ]

    if "question_input" not in st.session_state:
        st.session_state["question_input"] = ""

    st.markdown('<div class="sd-label">Example Questions</div>', unsafe_allow_html=True)
    pill_cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        if pill_cols[i].button(ex, key=f"pill_{i}"):
            st.session_state["question_input"] = ex
            st.rerun()

    question = st.text_area(
        "",
        value=st.session_state["question_input"],
        placeholder="Ask about crime safety in any Indian city…",
        height=100,
        key="qa_input",
        label_visibility="collapsed",
    )

    ask_clicked = st.button(
        "Ask SafeDistrict AI →",
        use_container_width=True,
        disabled=not (question or "").strip(),
    )

    if ask_clicked and (question or "").strip():
        with st.spinner("Consulting NCRB database..."):
            result = _post("/query", {"question": question})

        if result:
            query_type = result.get("query_type", "rag").upper()
            type_label_map = {
                "RAG": "Contextual Query",
                "ANOMALY": "Crime Spike Analysis",
                "COMPARE": "Comparison",
            }
            type_label = type_label_map.get(query_type, query_type)
            answer = result.get("answer", "No answer returned.")

            st.markdown(f"""
<div class="sd-ai-block" style="margin-top:24px">
  <div class="sd-label">{type_label}</div>
  <div style="font-size:14px;line-height:1.9;color:#e8e8f0">{answer}</div>
</div>
""", unsafe_allow_html=True)

            sources = result.get("sources", [])
            if sources:
                with st.expander("Sources used"):
                    for src in sources:
                        st.markdown(f"""
<div class="sd-panel" style="padding:12px 16px;margin-bottom:6px">
  <div style="font-size:13px;color:#8888aa">{src}</div>
</div>
""", unsafe_allow_html=True)
