"""Admin paneli route'ları — site yöneticisi.

Kimlik: imzalı admin token (security/admin_token). Tüm route'lar require_admin
ile korunur. FORCE-RLS tablolarına erişim için set_admin_rls çağrılır.
"""

from __future__ import annotations

import hmac
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.deps import require_admin, set_admin_rls
from app.models.appointment import Appointment
from app.models.sector import Sector
from app.models.service import Service
from app.models.staff_user import StaffUser
from app.models.station import Station
from app.models.tenant import Tenant
from app.models.user import User
from app.security.admin_token import make_admin_token

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Auth ---------------------------------------------------------------

class AdminLoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def admin_login(payload: AdminLoginRequest):
    s = get_settings()
    if not s.admin_email or not s.admin_password:
        raise HTTPException(status_code=403, detail="Admin paneli yapılandırılmamış")
    email_ok = hmac.compare_digest(payload.email.strip().lower(), s.admin_email.strip().lower())
    pass_ok = hmac.compare_digest(payload.password, s.admin_password)
    if not (email_ok and pass_ok):
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")
    return {"token": make_admin_token(), "email": s.admin_email}


# --- İstatistik ---------------------------------------------------------

@router.get("/stats")
async def stats(
    db: AsyncSession = Depends(get_db),
    _: Dict[str, Any] = Depends(require_admin),
):
    await set_admin_rls(db)
    businesses = await db.scalar(select(func.count()).select_from(Tenant))
    customers = await db.scalar(select(func.count()).select_from(User))
    appointments = await db.scalar(select(func.count()).select_from(Appointment))
    staff = await db.scalar(
        select(func.count()).select_from(StaffUser).where(StaffUser.role == "staff")
    )
    owners = await db.scalar(
        select(func.count()).select_from(StaffUser).where(StaffUser.role == "owner")
    )
    sectors = await db.scalar(select(func.count()).select_from(Sector))
    return {
        "businesses": businesses or 0,
        "customers": customers or 0,
        "appointments": appointments or 0,
        "staff": staff or 0,
        "owners": owners or 0,
        "sectors": sectors or 0,
    }


# --- Sektörler ----------------------------------------------------------

class SectorCreate(BaseModel):
    id: str = Field(min_length=2, max_length=50)
    label: str = Field(min_length=1, max_length=100)
    icon: str = Field(default="circle", max_length=100)
    services: List[str] = Field(default_factory=list)
    is_active: bool = True


class SectorUpdate(BaseModel):
    label: Optional[str] = Field(default=None, max_length=100)
    icon: Optional[str] = Field(default=None, max_length=100)
    services: Optional[List[str]] = None
    is_active: Optional[bool] = None


def _sector_public(s: Sector) -> Dict[str, Any]:
    return {
        "id": s.id,
        "label": s.label,
        "icon": s.icon,
        "services": (s.default_services or {}).get("items", []),
        "is_active": s.is_active,
    }


@router.get("/sectors")
async def list_sectors(
    db: AsyncSession = Depends(get_db),
    _: Dict[str, Any] = Depends(require_admin),
):
    rows = (await db.scalars(select(Sector).order_by(Sector.label))).all()
    return {"sectors": [_sector_public(s) for s in rows]}


@router.post("/sectors")
async def create_sector(
    payload: SectorCreate,
    db: AsyncSession = Depends(get_db),
    _: Dict[str, Any] = Depends(require_admin),
):
    sid = payload.id.strip().lower().replace(" ", "-")
    exists = await db.scalar(select(Sector).where(Sector.id == sid))
    if exists:
        raise HTTPException(status_code=409, detail="Bu kimlikte sektör zaten var")
    sector = Sector(
        id=sid,
        label=payload.label.strip(),
        icon=(payload.icon or "circle").strip(),
        default_services={"items": [x.strip() for x in payload.services if x.strip()]},
        is_active=payload.is_active,
    )
    db.add(sector)
    await db.flush()
    return {"sector": _sector_public(sector)}


@router.patch("/sectors/{sector_id}")
async def update_sector(
    sector_id: str,
    payload: SectorUpdate,
    db: AsyncSession = Depends(get_db),
    _: Dict[str, Any] = Depends(require_admin),
):
    sector = await db.scalar(select(Sector).where(Sector.id == sector_id))
    if not sector:
        raise HTTPException(status_code=404, detail="Sektör bulunamadı")
    if payload.label is not None:
        sector.label = payload.label.strip()
    if payload.icon is not None:
        sector.icon = payload.icon.strip()
    if payload.services is not None:
        sector.default_services = {"items": [x.strip() for x in payload.services if x.strip()]}
    if payload.is_active is not None:
        sector.is_active = payload.is_active
    await db.flush()
    return {"sector": _sector_public(sector)}


@router.delete("/sectors/{sector_id}")
async def delete_sector(
    sector_id: str,
    db: AsyncSession = Depends(get_db),
    _: Dict[str, Any] = Depends(require_admin),
):
    sector = await db.scalar(select(Sector).where(Sector.id == sector_id))
    if not sector:
        raise HTTPException(status_code=404, detail="Sektör bulunamadı")
    # Bu sektörü kullanan işletme varsa silme (FK RESTRICT) — gizle öner.
    in_use = await db.scalar(
        select(func.count()).select_from(Tenant).where(Tenant.sector_id == sector_id)
    )
    if in_use:
        raise HTTPException(
            status_code=409,
            detail=f"{in_use} işletme bu sektörü kullanıyor. Silmek yerine pasife al.",
        )
    await db.execute(delete(Sector).where(Sector.id == sector_id))
    return {"ok": True}


# --- İşletmeler ---------------------------------------------------------

@router.get("/businesses")
async def list_businesses(
    db: AsyncSession = Depends(get_db),
    _: Dict[str, Any] = Depends(require_admin),
):
    await set_admin_rls(db)
    tenants = (await db.scalars(select(Tenant).order_by(Tenant.created_at.desc()))).all()

    # Sektör etiketleri
    sector_rows = (await db.scalars(select(Sector))).all()
    sector_label = {s.id: s.label for s in sector_rows}

    # Personel/sahip + sayımlar
    owners = (await db.execute(
        select(StaffUser.business_id, StaffUser.gmail, StaffUser.name)
        .where(StaffUser.role == "owner")
    )).all()
    owner_map = {row[0]: {"gmail": row[1], "name": row[2]} for row in owners}

    staff_counts = dict((await db.execute(
        select(StaffUser.business_id, func.count()).group_by(StaffUser.business_id)
    )).all())
    appt_counts = dict((await db.execute(
        select(Appointment.business_id, func.count()).group_by(Appointment.business_id)
    )).all())

    out = []
    for t in tenants:
        owner = owner_map.get(t.id, {})
        out.append({
            "id": str(t.id),
            "name": t.name,
            "sector": sector_label.get(t.sector_id, t.sector_id),
            "location": t.location,
            "invite_code": t.invite_code,
            "verification_status": t.verification_status,
            "owner_name": owner.get("name"),
            "owner_gmail": owner.get("gmail"),
            "staff_count": int(staff_counts.get(t.id, 0)),
            "appointment_count": int(appt_counts.get(t.id, 0)),
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return {"businesses": out}


class BusinessUpdate(BaseModel):
    verification_status: Optional[str] = None


@router.patch("/businesses/{business_id}")
async def update_business(
    business_id: uuid.UUID,
    payload: BusinessUpdate,
    db: AsyncSession = Depends(get_db),
    _: Dict[str, Any] = Depends(require_admin),
):
    t = await db.scalar(select(Tenant).where(Tenant.id == business_id))
    if not t:
        raise HTTPException(status_code=404, detail="İşletme bulunamadı")
    if payload.verification_status is not None:
        t.verification_status = payload.verification_status.strip()
    await db.flush()
    return {"ok": True}


@router.delete("/businesses/{business_id}")
async def delete_business(
    business_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Dict[str, Any] = Depends(require_admin),
):
    await set_admin_rls(db)
    t = await db.scalar(select(Tenant).where(Tenant.id == business_id))
    if not t:
        raise HTTPException(status_code=404, detail="İşletme bulunamadı")
    # Sıralı sil: önce randevular (events + reminders cascade), sonra alt kayıtlar.
    await db.execute(delete(Appointment).where(Appointment.business_id == business_id))
    await db.execute(delete(Service).where(Service.business_id == business_id))
    await db.execute(delete(Station).where(Station.business_id == business_id))
    await db.execute(delete(StaffUser).where(StaffUser.business_id == business_id))
    await db.execute(delete(Tenant).where(Tenant.id == business_id))
    return {"ok": True}


# --- Müşteriler ---------------------------------------------------------

@router.get("/customers")
async def list_customers(
    db: AsyncSession = Depends(get_db),
    _: Dict[str, Any] = Depends(require_admin),
):
    rows = (await db.scalars(select(User).order_by(User.created_at.desc()))).all()
    return {
        "customers": [
            {
                "id": str(u.id),
                "name": f"{u.first_name} {u.last_name}".strip(),
                "phone_masked": u.phone_masked,
                "gmail": u.gmail,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in rows
        ]
    }


@router.delete("/customers/{customer_id}")
async def delete_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Dict[str, Any] = Depends(require_admin),
):
    u = await db.scalar(select(User).where(User.id == customer_id))
    if not u:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı")
    # appointments.customer_id ON DELETE SET NULL → randevular kalır, sahipsizleşir.
    await db.execute(delete(User).where(User.id == customer_id))
    return {"ok": True}
