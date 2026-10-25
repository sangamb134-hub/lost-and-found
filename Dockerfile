# ── Campus Lost and Found ── production Docker image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    FLASK_APP=wsgi.py \
    PORT=10000

WORKDIR /app

# System deps for Pillow + psycopg2
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Non-root user
RUN useradd -m appuser \
    && mkdir -p app/static/uploads \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE $PORT

# Run migrations + seed admin, then start gunicorn
# All in one CMD so it works on Render free tier (no preDeployCommand needed)
CMD flask db upgrade && flask seed-admin && gunicorn --bind "0.0.0.0:${PORT}" --workers 3 --timeout 120 wsgi:app
