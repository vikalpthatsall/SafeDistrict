"""
app.py — HuggingFace Spaces entry point for SafeDistrict AI.

Starts the FastAPI backend in a background subprocess on port 8000,
waits for it to be healthy, then renders the Streamlit frontend.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

import requests
import streamlit as st


# ---------------------------------------------------------------------------
# Backend lifecycle — cache_resource runs once per Spaces worker process.
# Subprocess stays alive for the lifetime of the worker.
# ---------------------------------------------------------------------------

@st.cache_resource
def _start_and_wait_backend() -> bool:
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "backend.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    health_url = "http://localhost:8000/health"
    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            if requests.get(health_url, timeout=2).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)

    proc.terminate()
    return False


backend_ok = _start_and_wait_backend()

if not backend_ok:
    st.set_page_config(page_title="SafeDistrict AI", page_icon="🏙️")
    st.error("⚠️ Backend failed to start within 90 seconds. Reload the page or check the logs.")
    st.stop()

# ---------------------------------------------------------------------------
# Frontend — exec frontend/app.py so st.set_page_config() is the first
# Streamlit call (Streamlit requirement) and all widgets render normally.
# ---------------------------------------------------------------------------

_frontend = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "app.py")
with open(_frontend) as _f:
    exec(compile(_f.read(), _frontend, "exec"))
