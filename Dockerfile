FROM python:3.11-slim

# Build tools for C extensions (chromadb, scikit-learn); curl for HEALTHCHECK.
# python:3.11-slim is debian:bookworm-slim-based and does NOT include curl —
# verified against the base image's own upstream Dockerfile (docker-library/
# python), which only adds ca-certificates/netbase/tzdata as runtime deps and
# uses wget (not curl) for its own build step.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Layer cache: deps change less often than source
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY data/ ./data/

# Non-root user. --create-home gives it a real home directory, and HOME is
# set explicitly rather than relying on that alone — sentence-transformers/
# huggingface_hub write the embedding + reranker model cache to
# ~/.cache/huggingface on first use (not something the app calls directly,
# but a real runtime write path), and if a base image ever leaves HOME=/root
# set from earlier root-user layers, os.path.expanduser("~") would still
# resolve there first and fail to write as this new user. chown /app covers
# the one path the app code explicitly writes to: rag_pipeline.py's
# chromadb/ persist directory (created relative to WORKDIR at runtime).
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
ENV HOME=/home/appuser
USER appuser

EXPOSE 8000 8501

# --start-period is generous because the first-ever boot downloads the
# embedding model (~90MB) and cross-encoder reranker model (~275MB) before
# the app can serve anything — observed to take a few minutes cold,
# seconds on subsequent starts once both are cached.
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
