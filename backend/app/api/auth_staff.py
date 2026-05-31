"""Personel auth: join (davet koduyla katıl) ve login."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.session import AuthSession
from app.models.staff_user import StaffUser
from app.models.tenant import Tenant
from app.schemas.auth import StaffJoinRequest, StaffLoginRequest
from app.schemas.common import AuthResponse, UserPublic
from app.security.passwords import hash_password, verify_password
from app.security.phones import encrypt_phone, mask_phone, normalize_phone, phone_hash
from app.security.tokens import new_session_token

router = APIRouter(prefix="/auth/staff", tags=["auth"])


def _make_staff_name(
    first_name: Optional[str], last_name: Optional[str], fallback: Optional[str]
) -> str:
    name = f"{(first_name or '').strip()} {(last_name or '').strip()}".strip()
    if name:
        return name
    if fallback and fallback.strip():
        return fallback.strip()
    raise HTTPException(status_code=400, detail="Personel adı ve soyadı gerekli")


def _staff_to_public(staff: StaffUser) -> UserPublic:
    return UserPublic(
        id=staff.id,
        name=staff.name,
        first_name=staff.first_name,
        last_name=staff.last_name,
        phone_masked=staff.phone_masked,
        gmail=staff.gmail,
        role="staff",
        business_id=staff.business_id,
        title=staff.title,
        station=staff.station_label,
    )


def _tenant_to_dict(tenant: Tenant) -> Dict[str, Any]:
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "sector": tenant.sector_id,
        "address": tenant.address,
        "location": tenant.location,
        "invite_code": tenant.invite_code,
        "verification_status": tenant.verification_status,
    }


@router.post("/join", response_model=AuthResponse)
async def join(payload: StaffJoinRequest, db: AsyncSession = Depends(get_db)):
    """Personel davet koduyla kayıt olur, kendi şifresini belirler.
    Sonraki girişler e-posta + şifre ile yapılır."""
    business = await db.scalar(
        select(Tenant).where(Tenant.invite_code == payload.invite_code.upper().strip())
    )
    if not business:
        raise HTTPException(status_code=404, detail="Davet kodu bulunamadı")

    email = payload.email.lower().strip()
    # Aynı e-posta ile zaten personel kaydı varsa engelle (giriş tekilliği için)
    existing = await db.scalar(
        select(StaffUser).where(StaffUser.gmail == email, StaffUser.role == "staff")
    )
    if existing:
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı, giriş yapın")

    staff_name = f"{payload.first_name.strip()} {payload.last_name.strip()}".strip()

    phone_enc = encrypt_phone(payload.phone) if payload.phone else None
    phone_h = phone_hash(payload.phone) if payload.phone else None
    phone_m = mask_phone(payload.phone) if payload.phone else None

    staff = StaffUser(
        id=uuid.uuid4(),
        business_id=business.id,
        role="staff",
        name=staff_name,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        phone_encrypted=phone_enc,
        phone_hash=phone_h,
        phone_masked=phone_m,
        gmail=email,
        password_hash=hash_password(payload.password),
        title=payload.title or "Çalışan",
    )
    db.add(staff)
    await db.flush()

    token = new_session_token()
    db.add(
        AuthSession(
            token=token,
            user_id=staff.id,
            principal_type="staff",
            business_id=business.id,
        )
    )

    return AuthResponse(
        token=token, user=_staff_to_public(staff), business=_tenant_to_dict(business)
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: StaffLoginRequest, db: AsyncSession = Depends(get_db)):
    """Personel girişi: e-posta + şifre (davet kodu gerekmez)."""
    email = payload.email.lower().strip()
    staff_list = (
        await db.scalars(
            select(StaffUser).where(StaffUser.gmail == email, StaffUser.role == "staff")
        )
    ).all()

    matched = next(
        (s for s in staff_list if verify_password(payload.password, s.password_hash)),
        None,
    )
    if not matched:
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")

    business = await db.scalar(select(Tenant).where(Tenant.id == matched.business_id))

    token = new_session_token()
    db.add(
        AuthSession(
            token=token,
            user_id=matched.id,
            principal_type="staff",
            business_id=matched.business_id,
        )
    )

    return AuthResponse(
        token=token,
        user=_staff_to_public(matched),
        business=_tenant_to_dict(business) if business else None,
    )
