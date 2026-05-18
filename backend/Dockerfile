# Backend Dockerfile — multilingual-rag
# Multi-stage: build deps with uv, then copy into slim runtime.
#
# Model weights are NOT baked in. Mount or download on first run via:
#   bash scripts/download_models.sh

# ---- Build stage: compile C extensions (zlib-state, lxml, faiss, etc.) ----
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dev headers needed to compile wheels (zlib-state needs zlib.h, lxml needs libxml2).
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

COPY app/ app/

# ---- Runtime: slim image with only shared libs, no dev headers ----
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime shared libs only (no -dev packages).
# libxml2 + libxslt1.1 for lxml; zlib1g is already in slim; curl for healthcheck.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libxml2 \
        libxslt1.1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
COPY pyproject.toml ./

# Ensure the venv's python is on PATH.
ENV PATH="/app/.venv/bin:$PATH"

# Data directories (mount points for volumes).
RUN mkdir -p data/models data/index data/sample_corpus data/benchmark

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
