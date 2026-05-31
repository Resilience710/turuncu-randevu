# syntax=docker/dockerfile:1.6
# Tek imaj: FastAPI (API + statik frontend). Build context = repo kökü.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STATIC_DIR=/app/static

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Bağımlılıklar (cache layer)
COPY backend/requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Backend kodu
COPY backend/app ./app
COPY backend/alembic.ini ./alembic.ini

# Statik frontend
COPY frontend/public ./static

EXPOSE 8000

# Her deploy'da migration koş, sonra uvicorn başlat
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
