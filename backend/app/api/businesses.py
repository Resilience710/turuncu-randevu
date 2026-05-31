"""İşletme route'ları: liste, detay, güncelleme."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_principal, require_owner, set_rls_context
from app.models.sector import Sector
from app.models.service import Service
from app.models.staff_user import StaffUser
from app.models.station import Station
from app.models.tenant import Tenant
from app.schemas.business import BusinessUpdateRequest

router = APIRouter(tags=["businesses"])


async def _services_for(db: AsyncSession, business_id: uuid.UUID) -> List[Dict[str, Any]]:
    rows = (
        await db.scalars(
            select(Service).where(Service.business_id == business_id).order_by(Service.name)
        )
    ).all()
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "duration_minutes": s.duration_minutes,
            "price": str(s.price) if s.price is not None else None,
        }
        for s in rows
    ]


async def _tenant_dict(
    db: AsyncSession,
    tenant: Tenant,
    *,
    include_employees: bool = False,
) -> Dict[str, Any]:
    sector_label = await db.scalar(
        select(Sector.label).where(Sector.id == tenant.sector_id)
    )
    employee_count = await db.scalar(
        select(func.count(StaffUser.id)).where(
            StaffUser.business_id == tenant.id,
            StaffUser.role.in_(("owner", "staff")),
        )
    )
    data: Dict[str, Any] = {
        "id": str(tenant.id),
        "name": tenant.name,
        "sector": tenant.sector_id,
        "sector_label": sector_label,
        "address": tenant.address,
        "location": tenant.location,
        "invite_code": tenant.invite_code,
        "verification_status": tenant.verification_status,
        "verification_note": tenant.verification_note,
        "services": await _services_for(db, tenant.id),
        "employee_count": int(employee_count or 0),
    }
    if include_employees:
        employees = (
            await db.scalars(
                select(StaffUser)
                .where(
                    StaffUser.business_id == tenant.id,
                    StaffUser.role.in_(("owner", "staff")),
                )
                .order_by(StaffUser.created_at)
            )
        ).all()
        data["employees"] = [
            {
                "id": str(e.id),
                "name": e.name,
                "first_name": e.first_name,
                "last_name": e.last_name,
                "phone_masked": e.phone_masked,
                "gmail": e.gmail,
                "role": e.role,
                "business_id": str(e.business_id),
                "title": e.title,
                "station": e.station_label,
                "station_ids": list(e.station_ids or []),
            }
            for e in employees
        ]
        stations = (
            await db.scalars(
                select(Station)
                .where(Station.business_id == tenant.id, Station.is_active.is_(True))
                .order_by(Station.position, Station.label)
            )
        ).all()
        data["stations"] = [
            {"id": str(st.id), "label": st.label, "position": st.position}
            for st in stations
        ]
    return data


@router.get("/businesses")
async def list_businesses(
    search: Optional[str] = None,
    sector: Optional[str] = None,
    location: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Public — herkes işletmeleri arayabilir. (tenants tablosunda RLS yok.)"""
    stmt = select(Tenant)
    conditions = []
    if sector and sector != "all":
        conditions.append(Tenant.sector_id == sector)
    if search:
        like = f"%{search}%"
        conditions.append(
            or_(Tenant.name.ilike(like), Tenant.address.ilike(like))
        )
    if location:
        conditions.append(Tenant.location.ilike(f"%{location}%"))
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(Tenant.created_at.desc()).limit(200)
    tenants = (await db.scalars(stmt)).all()
    return {
        "businesses": [await _tenant_dict(db, t) for t in tenants],
    }


@router.get("/businesses/{business_id}")
async def business_detail(business_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Public — işletme detay sayfası (müşteri rezervasyon ekranı için)."""
    tenant = await db.scalar(select(Tenant).where(Tenant.id == business_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="İşletme bulunamadı")
    return {"business": await _tenant_dict(db, tenant, include_employees=True)}


@router.put("/businesses/{business_id}")
async def update_business(
    business_id: uuid.UUID,
    payload: BusinessUpdateRequest,
    db: AsyncSession = Depends(get_db),
    principal: Dict[str, Any] = Depends(require_owner),
):
    """Sadece kendi işletmesinin sahibi düzenleyebilir."""
    if principal.get("business_id") != business_id:
        raise HTTPException(status_code=403, detail="Sadece kendi işletmenizi düzenleyebilirsiniz")

    await set_rls_context(db, principal)

    tenant = await db.scalar(select(Tenant).where(Tenant.id == business_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="İşletme bulunamadı")

    if payload.name is not None:
        tenant.name = payload.name.strip()
    if payload.address is not None:
        tenant.address = payload.address
    if payload.location is not None:
        tenant.location = payload.location
    if payload.sector is not None:
        sector = await db.scalar(select(Sector).where(Sector.id == payload.sector))
        if not sector:
            raise HTTPException(status_code=400, detail="Geçersiz sektör")
        tenant.sector_id = payload.sector
    if payload.verification_note is not None:
        tenant.verification_note = payload.verification_note

    # Hizmetler — full-replace stratejisi
    if payload.services is not None:
        existing = (
            await db.scalars(select(Service).where(Service.business_id == business_id))
        ).all()
        keep_ids = {s.id for s in payload.services if s.id}
        for svc in existing:
            if svc.id not in keep_ids:
                await db.delete(svc)
        for item in payload.services:
            if item.id:
                svc = next((s for s in existing if s.id == item.id), None)
                if svc:
                    svc.name = item.name
                    svc.duration_minutes = int(item.duration_minutes)
                    svc.price = item.price
                    continue
            db.add(
                Service(
                    id=uuid.uuid4(),
                    business_id=business_id,
                    name=item.name,
                    duration_minutes=int(item.duration_minutes),
                    price=item.price,
                )
            )

    await db.flush()
    return {"business": await _tenant_dict(db, tenant, include_employees=True)}
