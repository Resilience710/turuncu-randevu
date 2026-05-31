"""Sektör listesi ve KVKK metni endpoint'leri."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.sector import Sector
from app.services.seed import DEFAULT_KVKK_TEXT

router = APIRouter(tags=["public"])


@router.get("/sectors")
async def list_sectors(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.scalars(
            select(Sector).where(Sector.is_active.is_(True)).order_by(Sector.label)
        )
    ).all()
    return {
        "sectors": [
            {"id": s.id, "label": s.label, "icon": s.icon}
            for s in rows
        ]
    }


@router.get("/kvkk-text")
async def kvkk_text():
    return {"text": DEFAULT_KVKK_TEXT}
