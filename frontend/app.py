"""
app.py — Streamlit frontend for SafeDistrict AI.

Calls backend REST API only. Never imports backend modules directly.
"""

import html
import math
import os
import re
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# Makes `frontend.labels` importable regardless of launch mode (standalone
# `streamlit run frontend/app.py` vs. root app.py's exec() of this file for
# HF Spaces) — both are documented as run from the repo root, so "." is
# always correct. Same convention as backend/*.py's sys.path.insert(0, ".").
sys.path.insert(0, ".")

from frontend.labels import city_count_label

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
# Frontend never imports backend modules (see module docstring), so this
# reads the env var directly rather than backend.config.get_settings().
API_KEY = os.getenv("BACKEND_API_KEY", "")
_AUTH_HEADERS = {"X-API-Key": API_KEY}

# ── Design tokens ──────────────────────────────────────────────────────────────

# Root app.py exec()s this file, so __file__ can name the repo root instead;
# the labels module always knows where frontend/ is.
_FRONTEND_DIR = Path(sys.modules[city_count_label.__module__].__file__).resolve().parent

# Plotly and the favicon cannot read CSS custom properties, so they take their
# colours and fonts from tokens.css too: one palette for the page and the charts.
_TOKENS = dict(re.findall(r"--([\w-]+):\s*([^;]+);", (_FRONTEND_DIR / "tokens.css").read_text(encoding="utf-8")))
_SRGB_ROWS = (
    (4.0767416621, -3.3077115913, 0.2309699292),
    (-1.2684380046, 2.6097574011, -0.3413193965),
    (-0.0041960863, -0.7034186147, 1.7076147010),
)


def _rgb(name: str, alpha: float = 1) -> str:
    """The tokens.css colour --color-<name>, converted from oklch() to rgba()."""
    lightness, chroma, hue = (float(v) for v in re.findall(r"[\d.]+", _TOKENS[f"color-{name}"])[:3])
    big_l = lightness / 100
    a = chroma * math.cos(math.radians(hue))
    b = chroma * math.sin(math.radians(hue))
    lms = (
        (big_l + 0.3963377774 * a + 0.2158037573 * b) ** 3,
        (big_l - 0.1055613458 * a - 0.0638541728 * b) ** 3,
        (big_l - 0.0894841775 * a - 1.2914855480 * b) ** 3,
    )
    channels = []
    for row in _SRGB_ROWS:
        linear = sum(k * v for k, v in zip(row, lms))
        gamma = 12.92 * linear if linear <= 0.0031308 else 1.055 * linear ** (1 / 2.4) - 0.055
        channels.append(round(min(max(gamma, 0.0), 1.0) * 255))
    return "rgba({}, {}, {}, {})".format(*channels, alpha)


def _font(name: str) -> str:
    """The tokens.css font stack --font-<name>, without its quotes."""
    return _TOKENS[f"font-{name}"].replace('"', "").strip()


def _favicon() -> str:
    """The safety scale as a mark: a sunk slot on the midnight field and one lit index line."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        f'<rect width="64" height="64" rx="14" fill="{_rgb("paper")}"/>'
        f'<rect x="9" y="23" width="46" height="18" rx="5" fill="{_rgb("well")}" stroke="{_rgb("field")}" stroke-width="2"/>'
        f'<rect x="37" y="13" width="6" height="38" rx="3" fill="{_rgb("accent")}"/>'
        "</svg>"
    )


# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SafeDistrict AI",
    page_icon=_favicon(),
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS injection — must be first after set_page_config ───────────────────────

_IMPORT_RE = re.compile(r"""@import\s+url\(\s*["']?([^"')]+)["']?\s*\)\s*;""")


def _read_css(path: Path) -> str:
    """A stylesheet with its local @imports (tokens.css, base.css) inlined.

    The remote font @import stays where it is, ahead of every rule.
    """
    def _inline(match: re.Match) -> str:
        target = match.group(1)
        if "//" in target:
            return match.group(0)
        return _read_css(path.parent / target)

    return _IMPORT_RE.sub(_inline, path.read_text(encoding="utf-8"))


st.html("<style>" + _read_css(_FRONTEND_DIR / "styles.css") + "</style>")

# ── Chart layout template ──────────────────────────────────────────────────────


def _chart_layout() -> dict:
    """Shared layout: clear ground, hairline grid, mono ticks, labels in the body face."""
    clear = _rgb("paper", 0)
    return dict(
        paper_bgcolor=clear,
        plot_bgcolor=clear,
        font=dict(family=_font("body"), color=_rgb("ink-2"), size=13),
        margin=dict(l=8, r=56, t=8, b=48),
        showlegend=False,
        bargap=0.35,
        dragmode=False,
        separators=".,",
        xaxis=dict(
            nticks=5,
            tickformat=",",
            showgrid=True,
            gridcolor=_rgb("rule"),
            gridwidth=1,
            zeroline=False,
            showline=False,
            tickfont=dict(family=_font("outlier"), size=12, color=_rgb("muted")),
            title=dict(font=dict(family=_font("body"), size=12, color=_rgb("muted")), standoff=12),
            automargin=True,
            fixedrange=True,
        ),
        yaxis=dict(
            autorange="reversed",
            showgrid=False,
            zeroline=False,
            showline=False,
            tickfont=dict(family=_font("body"), size=13, color=_rgb("ink-2")),
            ticklabelstandoff=10,
            automargin=True,
            fixedrange=True,
        ),
        hoverlabel=dict(
            bgcolor=_rgb("paper-3"),
            bordercolor=_rgb("rule"),
            font=dict(family=_font("body"), size=13, color=_rgb("ink")),
        ),
        modebar=dict(bgcolor=clear, color=_rgb("muted"), activecolor=_rgb("ink")),
    )


_CHART_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "zoom2d", "pan2d", "select2d", "lasso2d",
        "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d",
    ],
}

# ── Offline error card ─────────────────────────────────────────────────────────

_OFFLINE_HTML = """
<div class="sd-offline" role="alert">
  <p class="sd-offline-title">Backend offline</p>
  <p>Start with: <code>uvicorn backend.main:app --reload</code></p>
</div>
"""


# ── Score color helper ─────────────────────────────────────────────────────────

# The API's own risk_level picks the colour, never a score threshold. Tones are
# styled in styles.css and match the tokens _rgb() reads for the charts.
_TONE = {"High": "risk", "Medium": "mid", "Moderate": "mid", "Low": "safe"}


def _tone(level) -> str:
    return _TONE.get(level, "mid")


# ── Markup helpers ─────────────────────────────────────────────────────────────

_CRIME_NAMES = {
    "murder": "Murder",
    "rape": "Rape",
    "kidnapping": "Kidnapping",
    "robbery": "Robbery",
    "burglary": "Burglary",
    "vehicle_theft": "Vehicle theft",
}


def _esc(value) -> str:
    return html.escape(str(value))


def _text(value) -> str:
    """A display string, or "" for a missing value (None, NaN)."""
    return value if isinstance(value, str) else ""


def _pagehead(title: str, meta: str, quiet: bool = False) -> str:
    # quiet steps the tab's title down when the screen's own subject (a city) is the head
    return (
        f'<div class="sd-pagehead{" sd-pagehead-quiet" if quiet else ""}"><h1 class="sd-title">{_esc(title)}</h1>'
        f'<p class="sd-meta">{_esc(meta)}</p></div>'
    )


def _stat(label: str, value: str, hint: str | None = None, swatch: str | None = None) -> str:
    mark = f'<span class="sd-swatch" data-tone="{swatch}"></span>' if swatch else ""
    note = f'<span class="sd-stat-hint">{_esc(hint)}</span>' if hint else ""
    return (
        f'<div class="sd-stat"><span class="sd-stat-label">{mark}{_esc(label)}</span>'
        f'<span class="sd-figure-value">{_esc(value)}</span>{note}</div>'
    )


def _city_cell(city, state, extra: str = "") -> str:
    state_html = f'<span class="sd-state">{_esc(state)}</span>' if _text(state) else ""
    return f'<span class="sd-city">{_esc(city)}{extra}</span>{state_html}'


def _dd(value) -> str:
    if value is None or str(value) in ("—", "", "None"):
        return '<span class="sd-missing">not reported</span>'
    return _esc(value)


def _bar_table(label_id: str, heads: str, body: str) -> str:
    return (
        f'<div class="sd-table-wrap" role="region" tabindex="0" aria-labelledby="{label_id}">'
        f'<table class="sd-table"><thead><tr>{heads}</tr></thead><tbody>{body}</tbody></table></div>'
    )


def _safety_scale(rows, *, above=(), below=(), legend=True, title=None, hint=None, dim=False, fill=None, summary=""):
    """The signature: every city's safety score as one tick on a 0 to 10 slot.

    rows are /top-dangerous profiles; each tick takes the tone of its own
    risk_level. above and below are (city, score, tone) marks named over or
    under the slot, each set on a machined cap. The half-way line marks the
    5.0 average. legend is True for the levels in rows, or the levels to key.
    fill is a (score, tone) level the slot fills up to. Every tick is named in
    its title and in a visually hidden list, so the cities can be told apart.
    """
    def clamp(score) -> float:
        return min(max(float(score or 0), 0.0), 10.0)

    def label(city, score, tone) -> str:
        s = clamp(score)
        align = "start" if s < 1.5 else "end" if s > 8.5 else "center"
        return (
            f'<span class="sd-scale-label" data-tone="{tone}" data-align="{align}" style="--x:{s * 10:.2f}%">'
            f'{_esc(city)} <span class="sd-num">{s:.1f}</span></span>'
        )

    def label_row(side, marks) -> str:
        if not marks:
            return ""
        return f'<div class="sd-scale-row" data-row="{side}">{"".join(label(*m) for m in marks)}</div>'

    head = []
    if title:
        head.append(f'<span class="sd-scale-title">{_esc(title)}</span>')
    if hint:
        head.append(f'<span class="sd-scale-hint">{_esc(hint)}</span>')
    if legend:
        order = {"High": 0, "Moderate": 1, "Medium": 1, "Low": 2}
        pool = [r.get("risk_level") for r in rows] if legend is True else list(legend)
        levels = sorted(set(pool) & set(_TONE), key=order.get)
        keys = "".join(
            f'<span class="sd-key" data-tone="{_tone(level)}"><span class="sd-swatch"></span>{_esc(level)} risk</span>'
            for level in levels
        )
        if keys:
            head.append(f'<span class="sd-legend">{keys}</span>')
    caption = f'<figcaption class="sd-scale-head">{"".join(head)}</figcaption>' if head else ""

    ticks = "".join(
        f'<span class="sd-tick" data-tone="{"dim" if dim else _tone(r.get("risk_level"))}" '
        f'title="{_esc(r.get("city", "?"))} {clamp(r.get("safety_score")):.1f}" '
        f'style="--x:{clamp(r.get("safety_score")) * 10:.2f}%"></span>'
        for r in rows
    )
    indexes = "".join(
        f'<span class="sd-index" data-tone="{tone}" title="{_esc(city)} {clamp(score):.1f}" '
        f'style="--x:{clamp(score) * 10:.2f}%"></span>'
        for marks in (above, below)
        for city, score, tone in marks
    )
    glow = (
        f'<span class="sd-fill" data-tone="{fill[1]}" style="--x:{clamp(fill[0]) * 10:.2f}%"></span>'
        if fill else ""
    )
    listed = "".join(
        f'<li>{_esc(r.get("city", "?"))}, {clamp(r.get("safety_score")):.1f}'
        + (f', {_esc(r.get("risk_level"))} risk' if r.get("risk_level") in _TONE else "")
        + "</li>"
        for r in sorted(rows, key=lambda r: clamp(r.get("safety_score")), reverse=True)
    )
    return (
        f'<figure class="sd-scale">{caption}'
        '<div class="sd-scale-body" aria-hidden="true">'
        f'{label_row("above", above)}'
        f'<div class="sd-slot"><div class="sd-track">{glow}<span class="sd-half"></span>{ticks}{indexes}</div></div>'
        f'{label_row("below", below)}'
        '<div class="sd-axis"><span>0</span><span>5</span><span>10</span></div>'
        "</div>"
        f'<div class="visually-hidden"><p>{_esc(summary)}</p><ol>{listed}</ol></div>'
        "</figure>"
    )


# ── API helpers ────────────────────────────────────────────────────────────────

def _get(path: str, **params):
    try:
        r = requests.get(f"{BASE_URL}{path}", params=params, headers=_AUTH_HEADERS, timeout=30)
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
        r = requests.post(f"{BASE_URL}{path}", json=payload, headers=_AUTH_HEADERS, timeout=60)
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

st.html('<p class="sd-wordmark">SafeDistrict AI</p>')
tab_dash, tab_city, tab_compare, tab_ask = st.tabs([
    "Dashboard", "City Explorer", "Compare", "Ask AI"
])


# ── PAGE 1 — Dashboard ─────────────────────────────────────────────────────────

with tab_dash:
    cities = get_cities()
    with st.spinner(f"Analyzing {city_count_label(cities)}…"):
        states = get_states()
        anomalies = get_anomalies()
        top_dangerous = get_top_dangerous(10)
        top1 = get_top_dangerous(1)
        women_safety = get_women_safety()
        scale_rows = get_top_dangerous(min(len(cities), 53)) if cities else []

    most_dangerous = top1[0].get("city", "—") if top1 else "—"
    anomaly_count = len(anomalies) if anomalies else 0

    head_stats = _stat("Cities monitored", f"{len(cities):,}") if cities else ""
    head_stats += _stat("Anomaly detected" if anomaly_count == 1 else "Anomalies detected", f"{anomaly_count:,}")
    page = [
        '<header class="sd-head">',
        _pagehead("India Crime Safety", "NCRB 2023, IPC crimes data"),
        f'<div class="sd-stats">{head_stats}</div>',
        "</header>",
    ]

    if scale_rows:
        ranked = sorted(scale_rows, key=lambda r: float(r.get("safety_score", 0) or 0))
        low_mark, high_mark = (
            (r.get("city", "?"), float(r.get("safety_score", 0) or 0), _tone(r.get("risk_level")))
            for r in (ranked[0], ranked[-1])
        )
        if len(ranked) == 1:
            above, below = [low_mark], []
        elif high_mark[1] - low_mark[1] >= 3.5:
            # Both ends are named above the slot unless the two names would collide
            above, below = [low_mark, high_mark], []
        else:
            above, below = [low_mark], [high_mark]
        summary = (
            f"Safety scores of {len(scale_rows)} cities on a 0 to 10 scale, higher is safer. "
            f"Lowest {low_mark[0]} at {low_mark[1]:.1f}, highest {high_mark[0]} at {high_mark[1]:.1f}."
        )
        page.append(
            '<div class="sd-panel">'
            + _safety_scale(scale_rows, above=above, below=below, title="Safety score",
                            hint="0 to 10, higher is safer", summary=summary)
            + "</div>"
        )

    kerala_note = (
        '<p class="sd-note">Higher rankings reflect higher FIR reporting rates, not necessarily higher '
        "crime incidence. Kerala cities consistently rank high due to stronger reporting culture, "
        "a finding consistent with published NCRB analysis.</p>"
    )
    col_left, col_right = [], []

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
            # Sort descending: highest risk at the top of the table
            df_top = df_top.sort_values(x_col, ascending=False)
            mean_val = df_top[x_col].mean()
            top_max = df_top[x_col].max() or 1
            avg_x = f"{mean_val / top_max * 100:.2f}%"
            top_body = "".join(
                f'<tr><td class="sd-rank">{rank}</td>'
                f'<td>{_city_cell(row["city"], row.get("state"))}</td>'
                f'<td class="sd-value sd-end">{row[x_col]:,.1f}</td>'
                '<td class="sd-bar-col" aria-hidden="true">'
                # each bar takes its city's risk_level, the key on the scale above
                + (f'<span class="sd-bar" data-tone="{_tone(row.get("risk_level"))}"'
                   if row.get("risk_level") in _TONE else '<span class="sd-bar"')
                + f' style="--w:{row[x_col] / top_max * 100:.2f}%"></span>'
                f'<span class="sd-bar-avg" style="--x:{avg_x}"></span></td></tr>'
                for rank, row in enumerate(df_top.to_dict("records"), start=1)
            )
            top_heads = (
                '<th scope="col">Rank</th><th scope="col">City</th>'
                '<th scope="col" class="sd-end">Per lakh</th>'
                f'<th scope="col" class="sd-bar-col"><span class="sd-avg-head" style="--x:{avg_x}">'
                f"average {mean_val:,.0f}</span></th>"
            )
            col_left.append(
                '<section class="sd-block" aria-labelledby="sd-top10">'
                '<h2 class="sd-h" id="sd-top10">Top 10 dangerous cities</h2>'
                '<p class="sd-sub">Crimes per lakh population</p>'
                + _bar_table("sd-top10", top_heads, top_body)
                + kerala_note
                + "</section>"
            )
            kerala_note = ""

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
            # Sort descending: highest risk at the top of the table
            df_women = df_women.sort_values("women_per_lakh", ascending=False)
            women_max = df_women["women_per_lakh"].max() or 1
            women_body = "".join(
                f'<tr><td class="sd-rank">{rank}</td>'
                f'<td>{_city_cell(row["city"], row.get("state"))}</td>'
                f'<td class="sd-value sd-end">{row["women_per_lakh"]:,.1f}</td>'
                '<td class="sd-bar-col" aria-hidden="true">'
                f'<span class="sd-bar" style="--w:{row["women_per_lakh"] / women_max * 100:.2f}%"></span></td></tr>'
                for rank, row in enumerate(df_women.to_dict("records"), start=1)
            )
            women_heads = (
                '<th scope="col">Rank</th><th scope="col">City</th>'
                '<th scope="col" class="sd-end">Per lakh</th>'
                '<th class="sd-bar-col" aria-hidden="true"></th>'
            )
            col_right.append(
                '<section class="sd-block" aria-labelledby="sd-women">'
                '<h2 class="sd-h" id="sd-women">Women safety risk index</h2>'
                '<p class="sd-sub">Crimes per lakh population</p>'
                + _bar_table("sd-women", women_heads, women_body)
                + kerala_note
                + "</section>"
            )

    # Anomaly section — all rows in a single table
    if anomalies:
        anomaly_rows_html = ""
        for a in anomalies:
            is_sev = a.get("is_severe", False)
            score = float(a.get("anomaly_score", 0))
            bar_w = min(int(score * 100), 100)
            tag = '<span class="sd-tag" data-state="severe">Severe</span>' if is_sev else ""
            pattern = str(a.get("crime_type", "") or "").replace("_", " ")
            pattern = pattern[:1].upper() + pattern[1:]
            anomaly_rows_html += (
                f'<tr><td>{_city_cell(a.get("city", "?"), a.get("state", ""), tag)}</td>'
                f"<td>{_dd(pattern)}</td>"
                f'<td class="sd-value sd-end">{score:.3f}</td>'
                '<td class="sd-bar-col" aria-hidden="true">'
                # neutral bars: the Severe tag carries severity, the risk tones stay with risk_level
                f'<span class="sd-bar" style="--w:{bar_w}%"></span></td></tr>'
            )
        anomaly_heads = (
            '<th scope="col">City</th><th scope="col">Pattern</th>'
            '<th scope="col" class="sd-end">Score</th>'
            '<th class="sd-bar-col" aria-hidden="true"></th>'
        )
        col_right.append(
            '<section class="sd-block" aria-labelledby="sd-anomalies">'
            '<h2 class="sd-h" id="sd-anomalies">Unusual crime patterns</h2>'
            '<p class="sd-sub">2023 data</p>'
            + _bar_table("sd-anomalies", anomaly_heads, anomaly_rows_html)
            + "</section>"
        )
    else:
        col_right.append(
            '<section class="sd-block" aria-labelledby="sd-anomalies">'
            '<h2 class="sd-h" id="sd-anomalies">Unusual crime patterns</h2>'
            '<p class="sd-sub">2023 data</p>'
            '<p class="sd-notice">No crime spike data available.</p>'
            "</section>"
        )

    page.append(
        f'<div class="sd-grid"><div class="sd-col">{"".join(col_left)}</div>'
        f'<div class="sd-col">{"".join(col_right)}</div></div>'
    )
    st.html("".join(page))


# ── PAGE 2 — City Explorer ─────────────────────────────────────────────────────

with tab_city:
    st.html(_pagehead("City Explorer", "Deep-dive into any city’s crime profile", quiet=True))

    cities_data = get_cities()
    if not cities_data:
        st.warning("Could not load city data. Is the backend running?")
    else:
        city_options = sorted(cities_data, key=lambda c: c["city"])
        display_names = [f"{c['city']} ({c.get('state', '')})" for c in city_options]
        city_for_display = {f"{c['city']} ({c.get('state', '')})": c["city"] for c in city_options}

        with st.container(key="city_pick"):
            selected_display = st.selectbox("City", display_names)
        selected = city_for_display[selected_display]

        with st.spinner("Consulting NCRB database…"):
            report = _get(f"/cities/{selected}")
            scale_rows = get_top_dangerous(min(len(cities_data), 53))

        if not report:
            st.warning("Could not load city report.")
        else:
            city_data = report.get("city_data", {})
            safety_score_val = float(report.get("safety_score", 0) or 0)
            is_anomaly = report.get("is_anomaly", False)
            rag_summary = report.get("rag_summary", "")
            risk_level = report.get("risk_level", "—")
            state = city_data.get("state", "")

            avg_delta = round(safety_score_val - 5.0, 1)
            delta_sign = "−" if avg_delta < 0 else "+"

            city_meta = [f"<span>{_esc(state)}</span>"] if _text(state) else []
            if risk_level in _TONE:
                city_meta.append(
                    f'<span class="sd-tag" data-tone="{_tone(risk_level)}">'
                    f'<span class="sd-swatch"></span>{_esc(risk_level)} risk</span>'
                )
            city_meta.append(
                '<span class="sd-tag" data-state="anomaly">Anomaly detected</span>'
                if is_anomaly else '<span class="sd-tag">No anomaly</span>'
            )

            readout = (
                '<div class="sd-stats">'
                + _stat("Safety score", f"{safety_score_val:.1f}", "out of 10, higher is safer")
                + _stat("vs. national average", f"{delta_sign}{abs(avg_delta):.1f}", "relative to 5.0 average score")
                + "</div>"
            )
            if scale_rows:
                # the city's own risk_level colours its cap and the fill; ink when the API has none
                city_tone = _tone(risk_level) if risk_level in _TONE else "ink"
                readout += _safety_scale(
                    scale_rows,
                    above=[(selected, safety_score_val, city_tone)],
                    fill=(safety_score_val, city_tone),
                    summary=(
                        f"{selected} scores {safety_score_val:.1f} on a 0 to 10 scale, "
                        f"shown among {len(scale_rows)} cities."
                    ),
                )

            st.html(
                f'<header class="sd-cityhead"><h2 class="sd-display">{_esc(selected)}</h2>'
                f'<div class="sd-citymeta">{"".join(city_meta)}</div></header>'
                f'<section class="sd-panel sd-readout" aria-label="Safety score">{readout}</section>'
            )

            col_chart, col_stats = st.columns([7, 5], gap="medium")

            crime_keys = ["murder", "rape", "kidnapping", "robbery", "burglary", "vehicle_theft"]
            crime_vals = {k: city_data.get(k, 0) or 0 for k in crime_keys}

            with col_chart:
                st.html(f'<h3 class="sd-h">Crime breakdown, {_esc(selected)}, 2023</h3>')
                ordered = sorted(crime_vals.items(), key=lambda kv: kv[1], reverse=True)
                fig = go.Figure(go.Bar(
                    x=[v for _, v in ordered],
                    y=[_CRIME_NAMES[k] for k, _ in ordered],
                    orientation="h",
                    # a neutral ink: the risk colours mean risk_level, and these are case counts
                    marker=dict(color=_rgb("ink-2"), line=dict(width=0), cornerradius=2),
                    text=[f"{int(v):,}" for _, v in ordered],
                    textposition="outside",
                    # the thin bars would otherwise shrink their value text to the bar's own 8px
                    constraintext="none",
                    cliponaxis=False,
                    textfont=dict(family=_font("outlier"), size=12, color=_rgb("ink-2")),
                    hovertemplate="%{y}: %{x:,}<extra></extra>",
                ))
                # bargap 0.8 thins the bars to about 8px, the same weight as the Dashboard's table bars
                fig.update_layout(_chart_layout(), height=300, bargap=0.8, xaxis_title_text="Reported cases")
                st.plotly_chart(fig, width="stretch", theme=None, config=_CHART_CONFIG)
                st.html('<p class="sd-note">Reported IPC cases by crime category. Source: NCRB 2023</p>')

            with col_stats:
                total_ipc = city_data.get("total_ipc", city_data.get("total_cognizable_ipc", "—"))
                cpl = city_data.get("crimes_per_lakh", "—")
                population = city_data.get("population", "—")
                women_risk = int((city_data.get("rape", 0) or 0) + (city_data.get("kidnapping", 0) or 0))

                total_ipc_fmt = f"{int(total_ipc):,}" if isinstance(total_ipc, (int, float)) else str(total_ipc)
                cpl_fmt = f"{cpl:,.1f}" if isinstance(cpl, float) else str(cpl)
                pop_fmt = f"{int(population):,}" if isinstance(population, (int, float)) else str(population)

                st.html(
                    '<h3 class="sd-h">City statistics</h3><dl class="sd-dl">'
                    f'<div><dt>Total IPC cases</dt><dd class="sd-value">{_dd(total_ipc_fmt)}</dd></div>'
                    f'<div><dt>Crimes per lakh</dt><dd class="sd-value">{_dd(cpl_fmt)}</dd></div>'
                    f'<div><dt>Population</dt><dd class="sd-value">{_dd(pop_fmt)}</dd></div>'
                    f'<div><dt>Women risk cases</dt><dd class="sd-value">{women_risk:,}</dd></div>'
                    f"<div><dt>Risk level</dt><dd>{_dd(risk_level)}</dd></div>"
                    "</dl>"
                )

            if rag_summary:
                with st.container(key="panel_assessment"):
                    st.html('<h3 class="sd-h">AI safety assessment</h3>')
                    st.markdown(rag_summary)


# ── PAGE 3 — Compare Cities ────────────────────────────────────────────────────

with tab_compare:
    st.html(_pagehead("Compare Cities", "Side-by-side safety analysis with an AI-powered verdict"))

    cities_data = get_cities()
    if not cities_data:
        st.warning("Could not load city data. Is the backend running?")
    else:
        city_options_c = sorted(cities_data, key=lambda c: c["city"])
        display_names_c = [f"{c['city']} ({c.get('state', '')})" for c in city_options_c]
        city_for_display_c = {f"{c['city']} ({c.get('state', '')})": c["city"] for c in city_options_c}

        col1, col2, col_go = st.columns([5, 5, 2], vertical_alignment="bottom", gap="medium")
        with col1:
            city1_display = st.selectbox("City 1", display_names_c, index=0, key="city1_sel")
            city1 = city_for_display_c[city1_display]
        with col2:
            default2 = 1 if len(display_names_c) > 1 else 0
            city2_display = st.selectbox("City 2", display_names_c, index=default2, key="city2_sel")
            city2 = city_for_display_c[city2_display]
        with col_go:
            compare_clicked = st.button("Compare", type="primary", disabled=city1 == city2, width="stretch")

        if city1 == city2:
            st.html('<p class="sd-notice" role="status">Select two different cities to compare.</p>')
        elif compare_clicked:
            with st.spinner("Generating AI analysis…"):
                result = _post("/compare", {"city1": city1, "city2": city2, "aspect": "overall safety"})
                r1 = _get(f"/cities/{city1}")
                r2 = _get(f"/cities/{city2}")
                scale_rows = get_top_dangerous(min(len(cities_data), 53))

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

                # Each city keeps the colour of its own risk_level, as on every other tab.
                tone1, tone2 = _tone(r1.get("risk_level")), _tone(r2.get("risk_level"))
                # The gap is the true one, as the old page printed it; a gap that shows as
                # 0.0 reads as a tie, never "0.0 points safer".
                if f"{score_diff:.1f}" == "0.0":
                    verdict_title = "Same safety score"
                    verdict_meta = (
                        f"{city1} and {city2} both score {s1:.1f} out of 10"
                        if f"{s1:.1f}" == f"{s2:.1f}"
                        else f"{city1} scores {s1:.1f} and {city2} scores {s2:.1f}, less than 0.1 apart"
                    )
                    above, below = [(city1, s1, tone1)], [(city2, s2, tone2)]
                else:
                    verdict_title = f"{safer_city} is the safer choice"
                    verdict_meta = f"{score_diff:.1f} points safer than {other_city}"
                    safer_tone, other_tone = (tone1, tone2) if safer_city == city1 else (tone2, tone1)
                    above = [(safer_city, max(s1, s2), safer_tone)]
                    below = [(other_city, min(s1, s2), other_tone)]

                verdict_stats = (
                    _stat(f"{city1}, {state1}" if _text(state1) else city1, f"{s1:.1f}",
                          "Safety score, out of 10", swatch=tone1)
                    + _stat(f"{city2}, {state2}" if _text(state2) else city2, f"{s2:.1f}",
                            "Safety score, out of 10", swatch=tone2)
                )
                verdict_scale = _safety_scale(
                    scale_rows, above=above, below=below, dim=True,
                    legend=[r1.get("risk_level"), r2.get("risk_level")],
                    summary=(
                        f"{city1} scores {s1:.1f} and {city2} scores {s2:.1f} on a 0 to 10 scale, "
                        f"shown among {len(scale_rows)} cities."
                    ),
                ) if scale_rows else ""

                st.html(
                    '<section class="sd-panel sd-verdict" aria-labelledby="sd-verdict">'
                    f'<h2 class="sd-display" id="sd-verdict">{_esc(verdict_title)}</h2>'
                    f'<p class="sd-meta">{_esc(verdict_meta)}</p>'
                    f'<div class="sd-readout"><div class="sd-stats">{verdict_stats}</div>{verdict_scale}</div>'
                    "</section>"
                    '<section class="sd-section" aria-labelledby="sd-method">'
                    '<h2 class="sd-h" id="sd-method">How the safety score is calculated</h2>'
                    '<p class="sd-prose">The safety score (0 to 10) is calculated from three factors: '
                    "<strong>crimes per lakh population</strong> (how the city compares to the national "
                    "average), <strong>crime type distribution</strong> (weighting violent crimes higher), "
                    "and <strong>statistical deviation</strong> from similar-sized cities. A score of 10 "
                    "means the safest possible city in the dataset. Source: NCRB 2023.</p>"
                    "</section>"
                )

                # Grouped bar chart
                d1 = r1.get("city_data", {})
                d2 = r2.get("city_data", {})
                crime_keys = ["murder", "rape", "kidnapping", "robbery", "burglary", "vehicle_theft"]
                v1 = [d1.get(k, 0) or 0 for k in crime_keys]
                v2 = [d2.get(k, 0) or 0 for k in crime_keys]
                crime_names = [_CRIME_NAMES[k] for k in crime_keys]

                st.html('<h2 class="sd-h sd-section">Crime comparison by category</h2>')

                bar_text = dict(family=_font("outlier"), size=12, color=_rgb("ink-2"))
                # The two series are told apart by fill, solid and outlined, in the neutral ink;
                # the risk colours stay with each city's risk_level on the scale above.
                series = (
                    (city1, v1, dict(color=_rgb("ink-2"), line=dict(width=0), cornerradius=2)),
                    (city2, v2, dict(color=_rgb("ink-2", 0), line=dict(color=_rgb("ink-2"), width=1.5), cornerradius=2)),
                )
                fig_cmp = go.Figure(data=[
                    go.Bar(name=city, y=crime_names, x=values, orientation="h",
                           marker=marker,
                           text=[f"{int(v):,}" for v in values], textposition="outside",
                           constraintext="none", cliponaxis=False, textfont=bar_text,
                           hovertemplate="%{fullData.name}, %{y}: %{x:,}<extra></extra>")
                    for city, values, marker in series
                ])
                fig_cmp.update_layout(
                    _chart_layout(),
                    barmode="group",
                    # about 8px bars, the weight of the table bars
                    bargap=0.62,
                    bargroupgap=0.2,
                    height=420,
                    showlegend=True,
                    margin=dict(t=40),
                    legend=dict(
                        orientation="h", x=0, xanchor="left", y=1.02, yanchor="bottom",
                        bgcolor=_rgb("paper", 0),
                        font=dict(family=_font("body"), size=13, color=_rgb("ink-2")),
                    ),
                )
                st.plotly_chart(fig_cmp, width="stretch", theme=None, config=_CHART_CONFIG)

            if result:
                answer = result.get("answer", str(result))
                with st.container(key="panel_compare"):
                    st.html('<h2 class="sd-h">AI comparative analysis</h2>')
                    st.markdown(answer)


# ── PAGE 4 — Ask AI ────────────────────────────────────────────────────────────

with tab_ask:
    st.html(_pagehead("Ask SafeDistrict AI", "Natural language queries, grounded in NCRB 2023 data"))

    examples = [
        "Is Delhi safe for women?",
        "Which city in Maharashtra has the highest crime?",
        "Compare Pune and Mumbai safety",
        "Are there crime spikes anywhere in 2023?",
    ]

    if "question_input" not in st.session_state:
        st.session_state["question_input"] = ""
    # A keyed text area keeps its own value across reruns and ignores a changed
    # value=, so the box is driven through its key: seeded once from
    # question_input here, and written by an example pill below.
    if "qa_input" not in st.session_state:
        st.session_state["qa_input"] = st.session_state["question_input"]

    st.html('<p class="sd-label">Example questions</p>')
    with st.container(horizontal=True, key="examples"):
        for i, ex in enumerate(examples):
            if st.button(ex, key=f"pill_{i}"):
                st.session_state["question_input"] = ex
                st.session_state["qa_input"] = ex
                st.rerun()

    question = st.text_area(
        "Your question",
        placeholder="Ask about crime safety in any Indian city…",
        height=100,
        key="qa_input",
    )
    question_empty = not (question or "").strip()

    with st.container(horizontal=True, vertical_alignment="center", key="ask_row"):
        ask_clicked = st.button(
            "Ask SafeDistrict AI",
            type="primary",
            disabled=question_empty,
        )
        if question_empty:
            st.html('<p class="sd-help">Write a question first.</p>')

    if ask_clicked and not question_empty:
        with st.spinner("Consulting NCRB database…"):
            result = _post("/query", {"question": question})

        if result:
            query_type = result.get("query_type", "rag").upper()
            type_label_map = {
                "RAG": "Contextual query",
                "ANOMALY": "Crime spike analysis",
                "COMPARE": "Comparison",
            }
            type_label = type_label_map.get(query_type, query_type.capitalize())
            answer = result.get("answer", "No answer returned.")

            with st.container(key="panel_answer"):
                st.html(f'<h2 class="sd-h">{_esc(type_label)}</h2>')
                st.markdown(answer)

            sources = result.get("sources", [])
            if sources:
                with st.expander("Sources used"):
                    source_items = ""
                    for src in sources:
                        city = src.get("city") or "General"
                        quality = src.get("data_quality", "")
                        excerpt = src.get("excerpt", "")
                        tier = f'<span class="sd-source-tier">{_esc(quality)}</span>' if quality else ""
                        source_items += (
                            f'<li><span class="sd-source-city">{_esc(city)}{tier}</span>'
                            f"<span>{_esc(excerpt)}</span></li>"
                        )
                    st.html(f'<ul class="sd-sources">{source_items}</ul>')
