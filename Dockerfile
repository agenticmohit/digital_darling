# ── Stage: runtime ────────────────────────────────────────────────────────────
FROM python:3.12-slim

# Install uv (fast Python package manager — replaces pip)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# ── Install dependencies ───────────────────────────────────────────────────────
# Copy only dependency files first so Docker can cache this layer.
# Re-runs only when requirements.txt or pyproject.toml changes.
COPY requirements.txt pyproject.toml ./
RUN uv pip install --system --no-cache -r requirements.txt

# ── Copy application code ──────────────────────────────────────────────────────
COPY . .

# ── Security: run as non-root ──────────────────────────────────────────────────
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

# ── Start ──────────────────────────────────────────────────────────────────────
# Railway injects $PORT at runtime. Default to 8000 for local docker runs.
# Use 2 workers — Railway Starter has 512 MB RAM which handles 2 comfortably.
CMD uvicorn main:app \
        --host 0.0.0.0 \
        --port ${PORT:-8000} \
        --workers 2 \
        --log-level info \
        --no-access-log
