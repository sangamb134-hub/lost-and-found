# ── Campus Lost and Found ── production Docker image
# Base: Python 3.12 slim (has pre-built wheels for Pillow 13 + psycopg2 2.9.13)
FROM python:3.12-slim

# ── Environment ────────────────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    FLASK_APP=wsgi.py \
    PORT=10000

WORKDIR /app

# ── System dependencies (Pillow + psycopg2) ────────────────────────────────────
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies (cached layer) ─────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ───────────────────────────────────────────────────────────
COPY . .

# ── Non-root user (security) ───────────────────────────────────────────────────
RUN useradd -m appuser \
    && mkdir -p app/static/uploads \
    && chown -R appuser:appuser /app
USER appuser

# ── Port ──────────────────────────────────────────────────────────────────────
EXPOSE $PORT

# ── Start command ─────────────────────────────────────────────────────────────
# Render sets $PORT at runtime; gunicorn binds to it.
# render.yaml preDeployCommand runs "flask db upgrade" before this starts.
CMD gunicorn --bind "0.0.0.0:${PORT}" --workers 3 --timeout 120 wsgi:app
