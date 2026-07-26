"""labels.py — plain-Python display-text helpers for frontend/app.py.

No streamlit import here: app.py's module-level st.set_page_config() and CSS
injection run at import time, which breaks under pytest. Keeping this file
Streamlit-free makes it importable and testable in isolation.
"""


def city_count_label(cities: list) -> str:
    """Human-readable city-count phrase for dashboard captions/spinners.
    Falls back to a generic phrase when the count is unknown (e.g. API unreachable),
    rather than showing a misleading '0 cities'.
    """
    count = len(cities)
    if count == 0:
        return "cities"
    return f"{count} cities"
