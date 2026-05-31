# syntax=docker/dockerfile:1.6

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Sistem bağımlılıkları (asyncpg derlemesi için minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Bağımlılık metadatasını kopyala ve kur (cache layer için)
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e .

# Uygulama kodu
COPY app ./app
COPY alembic.ini ./alembic.ini

EXPOSE 8000

# Her deploy'da migration koş, sonra uvicorn başlat
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
