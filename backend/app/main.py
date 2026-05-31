"""FastAPI uygulamasının giriş noktası."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama başlangıcı/kapanışı.

    NOT: Production'da migration'lar Docker CMD üzerinden `alembic upgrade head`
    ile koşar (bkz: backend/Dockerfile). Burada seed denenir ama DB hazır değilse
    sessizce geçilir.
    """
    import asyncio

    try:
        from app.services.seed import run_seed
        await run_seed()
        logger.info("Seed tamamlandı (idempotent).")
    except Exception as exc:
        logger.warning("Seed atlandı (DB henüz hazır değil olabilir): %s", exc)

    # SMS reminder worker — arka planda her 60 sn'de bir kontrol eder
    reminder_task: asyncio.Task | None = None
    try:
        from app.sms.reminders import reminder_worker
        reminder_task = asyncio.create_task(reminder_worker())
    except Exception as exc:
        logger.warning("Reminder worker başlatılamadı: %s", exc)

    yield

    if reminder_task and not reminder_task.done():
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Turuncu Randevu API",
    version="0.1.0",
    description="Multi-tenant randevu sistemi (FastAPI + Supabase Postgres)",
    lifespan=lifespan,
)

# Auth Bearer token ile (cookie yok). Dev'de her origin'e izin veriyoruz ki
# localhost / LAN IP / telefon — hepsi CORS'a takılmadan çalışsın.
# allow_credentials=False olunca "*" geçerli (spec gereği credentials ile "*" olmaz).
_cors_all = settings.cors_origins.strip() == "*" or not settings.is_production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _cors_all else settings.cors_origin_list,
    allow_credentials=False if _cors_all else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Beklenmeyen 500'leri JSON + CORS header'lı döndürür.

    Aksi halde ham 500 yanıtı CORS header'sız döner ve tarayıcıda
    yanlışlıkla 'CORS policy' hatası gibi görünür.
    """
    logger.error("Beklenmeyen sunucu hatası: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Sunucu hatası oluştu. Lütfen tekrar deneyin."},
    )


# --- Statik frontend (aynı origin'den sun) ---
# STATIC_DIR env varsa oradaki frontend dosyalarını "/" altında sunar.
# Böylece tek Render servisinde hem API (/api) hem site aynı origin'de.
_static_dir = os.getenv("STATIC_DIR", "").strip()
if _static_dir and Path(_static_dir).is_dir():
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
    logger.info("Statik frontend sunuluyor: %s", _static_dir)
else:
    @app.get("/")
    async def root():
        return {"name": "Turuncu Randevu API", "docs": "/docs", "api": "/api/"}
