"""Müsait randevu slotları (public — login gerektirmez)."""

from __future__ import annotations

import uuid
from datetime import date as _date, time as _time
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.staff_user import StaffUser
from app.models.tenant import Tenant
from app.services.slots import make_slots

router = APIRouter(tags=["availability"])


@router.get("/businesses/{business_id}/availability")
async def availability(
    business_id: uuid.UUID,
    staff_id: uuid.UUID = Query(...),
    date: _date = Query(...),
    db: AsyncSession = Depends(get_db),
):
    business = await db.scalar(select(Tenant).where(Tenant.id == business_id))
    staff = await db.scalar(
        select(StaffUser).where(
            StaffUser.id == staff_id, StaffUser.business_id == business_id
        )
    )
    if not business or not staff:
        raise HTTPException(status_code=404, detail="İşletme veya çalışan bulunamadı")

    appts = (
        await db.scalars(
            select(Appointment).where(
                Appointment.business_id == business_id,
                Appointment.staff_id == staff_id,
                Appointment.date == date,
                Appointment.status.in_(("booked", "in_service")),
            )
        )
    ).all()
    taken = {a.time.strftime("%H:%M") for a in appts}

    slots: List[dict] = [
        {"time": s, "status": "taken" if s in taken else "available"}
        for s in make_slots()
    ]
    return {"slots": slots}
