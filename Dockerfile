# Python image for the Lost and Found Management System
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

WORKDIR /app

# Install system dependencies for Pillow + psycopg2
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user for security
RUN useradd -m appuser \
    && mkdir -p app/static/uploads \
    && chown -R appuser:appuser /app
USER appuser

# Expose the port Render (and most hosts) expect
EXPOSE 8000

# Run with gunicorn. The app is in wsgi.py (module `wsgi`, callable `app`).
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "wsgi:app"]
