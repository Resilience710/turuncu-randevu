"""Çalışan (personel) route'ları: create, delete. Sadece işletme sahibi."""

from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import require_owner, set_rls_context
from app.models.appointment import Appointment
from app.models.staff_user import StaffUser
from app.models.station import Station
from app.schemas.employee import EmployeeCreateRequest
from app.security.passwords import hash_password
from app.security.phones import encrypt_phone, mask_phone, phone_hash

router = APIRouter(tags=["employees"])


def _make_name(
    first_name: str | None, last_name: str | None, fallback: str | None
) -> str:
    name = f"{(first_name or '').strip()} {(last_name or '').strip()}".strip()
    if name:
        return name
    if fallback and fallback.strip():
        return fallback.strip()
    raise HTTPException(status_code=400, detail="Personel adı ve soyadı gerekli")


def _employee_public(staff: StaffUser) -> Dict[str, Any]:
    return {
        "id": str(staff.id),
        "name": staff.name,
        "first_name": staff.first_name,
        "last_name": staff.last_name,
        "phone_masked": staff.phone_masked,
        "gmail": staff.gmail,
        "role": staff.role,
        "business_id": str(staff.business_id),
        "title": staff.title,
        "station": staff.station_label,
        "station_ids": list(staff.station_ids or []),
    }


@router.post("/employees")
async def create_employee(
    payload: EmployeeCreateRequest,
    db: AsyncSession = Depends(get_db),
    principal: Dict[str, Any] = Depends(require_owner),
):
    business_id = principal.get("business_id")
    if not business_id:
        raise HTTPException(status_code=403, detail="İşletme bilgisi yok")
    if not payload.email:
        raise HTTPException(status_code=400, detail="Personel girişi için e-posta gerekli")

    email = payload.email.lower().strip()
    dup = await db.scalar(
        select(StaffUser).where(StaffUser.gmail == email, StaffUser.role == "staff")
    )
    if dup:
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı")

    await set_rls_context(db, principal)

    name = _make_name(payload.first_name, payload.last_name, payload.name)
    first_name = payload.first_name or name.split(" ")[0]
    last_name = payload.last_name or " ".join(name.split(" ")[1:])

    phone_enc = encrypt_phone(payload.phone) if payload.phone else None
    phone_h = phone_hash(payload.phone) if payload.phone else None
    phone_m = mask_phone(payload.phone) if payload.phone else None

    # Seçilen istasyonları doğrula ve primary istasyonu belirle
    station_ids: list[str] = []
    primary_id = None
    primary_label = payload.station or None
    if payload.station_ids:
        rows = (
            await db.scalars(
                select(Station).where(
                    Station.id.in_(payload.station_ids),
                    Station.business_id == business_id,
                )
            )
        ).all()
        # payload sırasını koru
        by_id = {st.id: st for st in rows}
        ordered = [by_id[sid] for sid in payload.station_ids if sid in by_id]
        station_ids = [str(st.id) for st in ordered]
        if ordered:
            primary_id = ordered[0].id
            primary_label = ordered[0].label

    employee = StaffUser(
        id=uuid.uuid4(),
        business_id=business_id,
        role="staff",
        name=name,
        first_name=first_name,
        last_name=last_name,
        phone_encrypted=phone_enc,
        phone_hash=phone_h,
        phone_masked=phone_m,
        gmail=payload.email.lower().strip() if payload.email else None,
        password_hash=hash_password(payload.password),
        title=payload.title or "Çalışan",
        station_id=primary_id,
        station_label=primary_label,
        station_ids=station_ids,
    )
    db.add(employee)
    await db.flush()
    return {"employee": _employee_public(employee)}


@router.delete("/employees/{employee_id}")
async def delete_employee(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    principal: Dict[str, Any] = Depends(require_owner),
):
    business_id = principal.get("business_id")
    await set_rls_context(db, principal)

    employee = await db.scalar(
        select(StaffUser).where(
            StaffUser.id == employee_id,
            StaffUser.business_id == business_id,
            StaffUser.role == "staff",
        )
    )
    if not employee:
        raise HTTPException(status_code=404, detail="Çalışan bulunamadı")

    active = await db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.staff_id == employee_id,
            Appointment.status.in_(("booked", "in_service")),
        )
    )
    if active and int(active) > 0:
        raise HTTPException(
            status_code=409, detail="Aktif randevusu olan çalışan silinemez"
        )

    await db.delete(employee)
    await db.flush()
    return {"deleted": True, "id": str(employee_id)}
