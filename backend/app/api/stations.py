"""İstasyon route'ları: liste, CRUD ve canlı doluluk (occupancy)."""

from __future__ import annotations

import uuid
from datetime import date as _date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import (
    get_current_principal,
    require_owner,
    require_staff_or_owner,
    set_rls_context,
)
from app.models.appointment import Appointment
from app.models.staff_user import StaffUser
from app.models.station import Station
from app.schemas.station import StationCreateRequest, StationUpdateRequest

router = APIRouter(tags=["stations"])


def _station_dict(s: Station) -> Dict[str, Any]:
    return {
        "id": str(s.id),
        "label": s.label,
        "position": s.position,
        "is_active": s.is_active,
    }


@router.get("/stations")
async def list_stations(
    db: AsyncSession = Depends(get_db),
    principal: Dict[str, Any] = Depends(require_staff_or_owner),
):
    """Patron + personel için: işletmenin istasyon listesi."""
    business_id = principal.get("business_id")
    if not business_id:
        raise HTTPException(status_code=403, detail="İşletme bilgisi yok")

    await set_rls_context(db, principal)

    rows = (
        await db.scalars(
            select(Station)
            .where(Station.business_id == business_id)
            .order_by(Station.position, Station.label)
        )
    ).all()
    return {"stations": [_station_dict(s) for s in rows]}


@router.post("/stations")
async def create_station(
    payload: StationCreateRequest,
    db: AsyncSession = Depends(get_db),
    principal: Dict[str, Any] = Depends(require_owner),
):
    business_id = principal.get("business_id")
    await set_rls_context(db, principal)

    station = Station(
        id=uuid.uuid4(),
        business_id=business_id,
        label=payload.label.strip(),
        position=payload.position,
        is_active=True,
    )
    db.add(station)
    await db.flush()
    return {"station": _station_dict(station)}


@router.patch("/stations/{station_id}")
async def update_station(
    station_id: uuid.UUID,
    payload: StationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    principal: Dict[str, Any] = Depends(require_owner),
):
    business_id = principal.get("business_id")
    await set_rls_context(db, principal)

    station = await db.scalar(
        select(Station).where(
            Station.id == station_id, Station.business_id == business_id
        )
    )
    if not station:
        raise HTTPException(status_code=404, detail="İstasyon bulunamadı")
    if payload.label is not None:
        station.label = payload.label.strip()
    if payload.position is not None:
        station.position = payload.position
    if payload.is_active is not None:
        station.is_active = payload.is_active
    await db.flush()
    return {"station": _station_dict(station)}


@router.delete("/stations/{station_id}")
async def delete_station(
    station_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    principal: Dict[str, Any] = Depends(require_owner),
):
    business_id = principal.get("business_id")
    await set_rls_context(db, principal)

    station = await db.scalar(
        select(Station).where(
            Station.id == station_id, Station.business_id == business_id
        )
    )
    if not station:
        raise HTTPException(status_code=404, detail="İstasyon bulunamadı")

    # Aktif randevu varsa engelle
    active = await db.scalar(
        select(Appointment.id).where(
            Appointment.station_id == station_id,
            Appointment.status.in_(("booked", "in_service")),
        )
    )
    if active:
        raise HTTPException(
            status_code=409, detail="Aktif randevusu olan istasyon silinemez"
        )
    await db.delete(station)
    await db.flush()
    return {"deleted": True, "id": str(station_id)}


# --- OCCUPANCY (canlı doluluk) ---


def _appt_brief(a: Appointment) -> Dict[str, Any]:
    return {
        "id": str(a.id),
        "staff_id": str(a.staff_id),
        "service_name": a.service_name,
        "customer_name": a.customer_name,
        "customer_phone_masked": a.customer_phone_masked,
        "time": a.time.strftime("%H:%M"),
        "status": a.status,
        "started_at": a.started_at.isoformat() if a.started_at else None,
    }


@router.get("/stations/occupancy")
async def occupancy(
    db: AsyncSession = Depends(get_db),
    principal: Dict[str, Any] = Depends(require_staff_or_owner),
):
    """Patron dashboard'unun 5 sn'de bir polled ettiği endpoint.

    Her aktif istasyon için:
      - status: 'in_service' | 'waiting' | 'idle'
      - current_appointment: şu an işlemde olan randevu (varsa)
      - next_appointment: bugün için sıradaki rezerve randevu (varsa)
    """
    business_id = principal.get("business_id")
    if not business_id:
        raise HTTPException(status_code=403, detail="İşletme bilgisi yok")

    await set_rls_context(db, principal)

    today = datetime.now(timezone.utc).date()

    stations = (
        await db.scalars(
            select(Station)
            .where(Station.business_id == business_id, Station.is_active.is_(True))
            .order_by(Station.position, Station.label)
        )
    ).all()

    # Her istasyona bağlı personeller: hem primary station_id hem de
    # çoklu station_ids (jsonb) üzerinden eşleştir.
    station_to_staff_ids: Dict[uuid.UUID, List[uuid.UUID]] = {s.id: [] for s in stations}
    all_staff = (
        await db.scalars(
            select(StaffUser).where(StaffUser.business_id == business_id)
        )
    ).all()
    for st in all_staff:
        linked = set()
        if st.station_id is not None:
            linked.add(str(st.station_id))
        for sid in (st.station_ids or []):
            linked.add(str(sid))
        for s in stations:
            if str(s.id) in linked:
                station_to_staff_ids[s.id].append(st.id)

    # Bugünün randevuları
    appts = (
        await db.scalars(
            select(Appointment)
            .where(
                Appointment.business_id == business_id,
                Appointment.date == today,
                Appointment.status.in_(("booked", "in_service")),
            )
            .order_by(Appointment.time)
        )
    ).all()

    # Personel -> primary istasyon (station_id yoksa fallback için)
    staff_primary: Dict[uuid.UUID, uuid.UUID] = {}
    station_id_set = {s.id for s in stations}
    for st in all_staff:
        prim = None
        if st.station_id in station_id_set:
            prim = st.station_id
        elif st.station_ids:
            for sid in st.station_ids:
                try:
                    cand = uuid.UUID(str(sid))
                except (ValueError, TypeError):
                    continue
                if cand in station_id_set:
                    prim = cand
                    break
        if prim is not None:
            staff_primary[st.id] = prim

    # Her randevuyu TEK bir istasyona ata (çift gösterimi önler)
    appts_by_station: Dict[uuid.UUID, List[Appointment]] = {s.id: [] for s in stations}
    for a in appts:
        target = a.station_id if a.station_id in station_id_set else staff_primary.get(a.staff_id)
        if target in appts_by_station:
            appts_by_station[target].append(a)

    results: List[Dict[str, Any]] = []
    for s in stations:
        related = appts_by_station[s.id]
        current = next((a for a in related if a.status == "in_service"), None)
        next_a = next((a for a in related if a.status == "booked"), None)
        if current:
            status = "in_service"
        elif next_a:
            status = "waiting"
        else:
            status = "idle"
        results.append(
            {
                "id": str(s.id),
                "label": s.label,
                "position": s.position,
                "status": status,
                "current_appointment": _appt_brief(current) if current else None,
                "next_appointment": _appt_brief(next_a) if next_a else None,
            }
        )

    return {
        "stations": results,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
