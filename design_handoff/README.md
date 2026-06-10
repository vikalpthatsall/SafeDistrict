# Handoff: SafeDistrict UI Redesign

## Overview
This is a high-fidelity redesign of `frontend/app.py` — the Streamlit dashboard for SafeDistrict AI. The goal is to replace the current generic dark theme with a minimalist, typographically-driven design that feels like a proper civic data product rather than a generated dashboard.

The HTML file `SafeDistrict Redesign.html` in this folder is the **pixel-perfect design reference**. Do not ship the HTML — use it as a visual target while rewriting `frontend/app.py`.

---

## Fidelity
**High-fidelity.** Match the prototype exactly: colors, spacing, typography, component structure, and behaviour. Every design value below is final.

---

## What Changes

| Area | Before | After |
|---|---|---|
| Navigation | `st.sidebar.radio()` | `st.tabs()` — top tab bar |
| Sidebar | Visible, used for nav + model info | **Hidden entirely** via CSS |
| Fonts | DM Sans + DM Mono | Bricolage Grotesque (headings) + Manrope (body) + JetBrains Mono (numbers) |
| Cards | Left-border accent cards (`border-left: 3px solid #color`) | Clean panels — subtle border, no accent border |
| Section headers | ALL-CAPS with bottom border on every section | Sparse: only where genuinely labelling a section |
| Page titles | `<span style="color:#f59e0b">` coloured word | Plain Bricolage Grotesque, no coloured span |
| Metric grid | 4 equal `st.columns` metric cards at top of dashboard | Removed — replaced with inline meta line in page header |
| Anomaly list | Heavy card per anomaly | Clean CSS Grid table rows with dot indicator + thin progress bar |
| Background | `#080d1a` | `#0d0d10` |
| Primary text | `#e2e8f0` | `#e8e8f0` |
| Secondary text | `#475569` (very low contrast) | `#8888aa` (readable) |
| Muted / label text | `#2d3f5e` | `#505068` |

---

## Design Tokens

Paste these as CSS custom properties in the `st.markdown()` CSS block:

```css
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,300;12..96,400;12..96,500;12..96,600&family=Manrope:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --font-display: 'Bricolage Grotesque', sans-serif;
  --font-body:    'Manrope', sans-serif;
  --font-mono:    'JetBrains Mono', monospace;

  /* Dark theme (default) */
  --bg:      #0d0d10;
  --surf:    #131318;
  --surf2:   #1a1a22;
  --bdr:     #252530;
  --bdr-s:   #1c1c26;
  --tx:      #e8e8f0;
  --tx2:     #8888aa;   /* secondary text — readable */
  --tx3:     #505068;   /* labels / muted */
  --danger:  #e84040;
  --warn:    #e8a020;
  --safe:    #20c8a0;
}
```

---

## Navigation: Switch to st.tabs()

**Remove** the entire sidebar block. **Replace** with `st.tabs()`:

```python
# REMOVE THIS:
st.sidebar.markdown(...)
page = st.sidebar.radio("", ["Dashboard", "City Explorer", "Compare Cities", "Ask AI"], ...)

# ADD THIS:
tab_dash, tab_city, tab_compare, tab_ask = st.tabs([
    "Dashboard", "City Explorer", "Compare", "Ask AI"
])

# Then use:
with tab_dash:
    render_dashboard()

with tab_city:
    render_city_explorer()

with tab_compare:
    render_compare()

with tab_ask:
    render_ask_ai()
```

Style the tabs via CSS to match the prototype's top nav look (see CSS section below).

---

## CSS Block (full replacement)

Replace the entire existing `st.markdown("""<style>...</style>""")` block with:

```python
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
```

---

## Page-by-Page Breakdown

### Dashboard

**Header HTML:**
```python
st.markdown("""
<div class="sd-page-title">India Crime Safety</div>
<div class="sd-page-meta">53 cities monitored · 18 anomalies detected · NCRB 2023 · IPC crimes data</div>
""", unsafe_allow_html=True)
```

**Anomaly row HTML pattern** (replace the existing anomaly card loop):
```python
for a in anomalies:
    is_sev = a.get("is_severe", False)
    score  = float(a.get("anomaly_score", 0))
    bar_w  = min(int(score * 100), 100)
    dot_c  = "sd-dot-sev" if is_sev else "sd-dot-mod"
    bar_c  = "sd-bar-fill-sev" if is_sev else "sd-bar-fill-mod"
    score_c= "sev" if is_sev else "mod"
    st.markdown(f"""
    <div class="sd-anomaly-row">
      <div>
        <div class="sd-anomaly-city">{a.get('city','?')}</div>
        <div class="sd-anomaly-meta">{a.get('state','')} · {a.get('crime_type','')}</div>
      </div>
      <div class="sd-dot {dot_c}"></div>
      <div class="sd-bar-track">
        <div class="{bar_c}" style="width:{bar_w}%"></div>
      </div>
      <div class="sd-score-val {score_c}">{score:.3f}</div>
    </div>
    """, unsafe_allow_html=True)
```

**Plotly chart config** — update `CHART_LAYOUT`:
```python
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
```

---

### City Explorer

**City hero:**
```python
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
```

**Score panels:**
```python
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
    <div class="sd-panel">
      <div class="sd-label">Safety Score</div>
      <div class="sd-score" style="color:{score_color}">{safety_score:.1f}</div>
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
```

**Stats table:**
```python
st.markdown(f"""
<div class="sd-panel">
  <div class="sd-label">City Statistics</div>
  <div class="sd-stat-row"><span class="sd-stat-k">Total IPC Cases</span><span class="sd-stat-v">{total_ipc_fmt}</span></div>
  <div class="sd-stat-row"><span class="sd-stat-k">Crimes per Lakh</span><span class="sd-stat-v">{cpl_fmt}</span></div>
  <div class="sd-stat-row"><span class="sd-stat-k">Population</span><span class="sd-stat-v">{pop_fmt}</span></div>
  <div class="sd-stat-row"><span class="sd-stat-k">Women Risk Cases</span><span class="sd-stat-v">{women_risk:,}</span></div>
  <div class="sd-stat-row"><span class="sd-stat-k">Risk Level</span><span class="sd-stat-v" style="color:{score_color}">{risk_level}</span></div>
</div>
""", unsafe_allow_html=True)
```

**AI assessment:**
```python
if rag_summary:
    st.markdown(f"""
    <div class="sd-ai-block">
      <div class="sd-ai-label">AI Safety Assessment</div>
      <div class="sd-ai-text">{rag_summary}</div>
    </div>
    """, unsafe_allow_html=True)
```

---

### Compare Cities

**Winner banner:**
```python
st.markdown(f"""
<div class="sd-verdict">
  <div class="sd-verdict-label">Safer Choice</div>
  <div class="sd-verdict-city">{safer_city}</div>
  <div class="sd-verdict-delta">{score_diff:.1f} points safer than {other_city}</div>
</div>
""", unsafe_allow_html=True)
```

**Score cards (2 columns):**
```python
mc1, mc2 = st.columns(2)
with mc1:
    st.markdown(f"""
    <div class="sd-panel">
      <div class="sd-label">{city1} · {state1}</div>
      <div class="sd-score" style="color:{s1_color}">{s1:.1f}</div>
      <div class="sd-score-sub">Safety Score / 10</div>
    </div>
    """, unsafe_allow_html=True)
```

---

### Ask AI

**Header:**
```python
st.markdown("""
<div class="sd-page-title">Ask SafeDistrict AI</div>
<div class="sd-page-meta">Natural language queries · Grounded in NCRB 2023 data</div>
""", unsafe_allow_html=True)
```

**Response block:**
```python
st.markdown(f"""
<div class="sd-ai-block" style="margin-top:24px">
  <div class="sd-label">{query_type}</div>
  <div style="font-size:14px;line-height:1.9;color:#e8e8f0">{answer}</div>
</div>
""", unsafe_allow_html=True)
```

---

## Score Color Helper

```python
def score_color(score: float) -> str:
    if score <= 4:   return "#e84040"   # danger
    elif score <= 6: return "#e8a020"   # warn
    else:            return "#20c8a0"   # safe
```

---

## Files in This Package

| File | Purpose |
|---|---|
| `SafeDistrict Redesign.html` | Complete interactive prototype — open in browser to see target design |
| `README.md` | This file — implementation spec for Claude Code |

## How to Use with Claude Code

In your terminal inside the repo, run Claude Code and give it this prompt:

```
Read design_handoff/README.md fully, then open design_handoff/SafeDistrict Redesign.html in a browser to see the visual target.

Rewrite frontend/app.py to match the redesign:
1. Replace the entire CSS st.markdown block with the one in the README
2. Replace st.sidebar.radio() navigation with st.tabs() as described
3. Replace all sd-card / anomaly HTML with the new HTML patterns from the README
4. Keep all backend API calls, caching, and data logic exactly as-is — only change the presentation layer
5. Update CHART_LAYOUT to the new values in the README

Do not change any API endpoints, caching decorators, or data processing logic.
```
