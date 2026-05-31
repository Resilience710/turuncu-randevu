"""İşletme sahibi auth: register, login."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.sector import Sector
from app.models.service import Service
from app.models.session import AuthSession
from app.models.staff_user import StaffUser
from app.models.station import Station
from app.models.tenant import Tenant
from app.schemas.auth import OwnerLoginRequest, OwnerRegisterRequest
from app.schemas.common import AuthResponse, UserPublic
from app.security.passwords import hash_password, verify_password
from app.security.phones import encrypt_phone, mask_phone, normalize_phone, phone_hash
from app.security.tokens import new_invite_code, new_session_token

router = APIRouter(prefix="/auth/owner", tags=["auth"])


def _staff_to_public(staff: StaffUser, role: str = "owner") -> UserPublic:
    return UserPublic(
        id=staff.id,
        name=staff.name,
        first_name=staff.first_name,
        last_name=staff.last_name,
        phone_masked=staff.phone_masked,
        gmail=staff.gmail,
        role=role,  # type: ignore[arg-type]
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
        "verification_note": tenant.verification_note,
    }


async def _seed_default_services(db: AsyncSession, business_id: uuid.UUID, sector_id: str) -> None:
    sector = await db.scalar(select(Sector).where(Sector.id == sector_id))
    items = []
    if sector and isinstance(sector.default_services, dict):
        items = sector.default_services.get("items", [])
    if not items:
        items = ["Standart Hizmet"]
    for name in items:
        db.add(
            Service(
                id=uuid.uuid4(),
                business_id=business_id,
                name=name,
                duration_minutes=30,
            )
        )


@router.post("/register", response_model=AuthResponse)
async def register(payload: OwnerRegisterRequest, db: AsyncSession = Depends(get_db)):
    if not payload.phone and not payload.gmail:
        raise HTTPException(status_code=400, detail="Telefon veya e-posta gerekli")

    # Sektör doğrulaması
    sector = await db.scalar(select(Sector).where(Sector.id == payload.sector))
    if not sector:
        raise HTTPException(status_code=400, detail="Geçersiz sektör")

    business_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    invite = new_invite_code()
    # Eşsizliği garanti et (çok küçük olasılık ama yine de döngü)
    while await db.scalar(select(Tenant).where(Tenant.invite_code == invite)):
        invite = new_invite_code()

    tenant = Tenant(
        id=business_id,
        owner_id=owner_id,
        name=payload.business_name.strip(),
        sector_id=payload.sector,
        address=payload.address or "Adres eklenmedi",
        location=payload.location or "Konum seçilmedi",
        invite_code=invite,
        verification_status="beklemede",
        verification_note="İşletme doğrulaması sonraki adımda tamamlanacak.",
    )
    db.add(tenant)
    # FK bağımlı insert'lerden (services, staff_users) önce tenant'ı DB'ye yaz.
    # autoflush kapalı olduğu için bunu açıkça yapmak zorundayız.
    await db.flush()

    await _seed_default_services(db, business_id, payload.sector)

    phone_enc = encrypt_phone(payload.phone) if payload.phone else None
    phone_h = phone_hash(payload.phone) if payload.phone else None
    phone_m = mask_phone(payload.phone) if payload.phone else None

    owner = StaffUser(
        id=owner_id,
        business_id=business_id,
        role="owner",
        name=payload.name.strip(),
        phone_encrypted=phone_enc,
        phone_hash=phone_h,
        phone_masked=phone_m,
        gmail=payload.gmail.lower() if payload.gmail else None,
        password_hash=hash_password(payload.password),
        title="İşletme Sahibi",
        station_label="Yönetim",
    )
    db.add(owner)
    await db.flush()

    token = new_session_token()
    db.add(
        AuthSession(
            token=token,
            user_id=owner_id,
            principal_type="staff",
            business_id=business_id,
        )
    )

    return AuthResponse(
        token=token,
        user=_staff_to_public(owner, role="owner"),
        business=_tenant_to_dict(tenant),
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: OwnerLoginRequest, db: AsyncSession = Depends(get_db)):
    ident = payload.identifier.lower().strip()

    # Önce gmail ile dene
    user: Optional[StaffUser] = await db.scalar(
        select(StaffUser).where(StaffUser.role == "owner", StaffUser.gmail == ident)
    )
    # Olmadıysa telefon ile dene
    if not user:
        try:
            ph_hash = phone_hash(payload.identifier)
            user = await db.scalar(
                select(StaffUser).where(
                    StaffUser.role == "owner", StaffUser.phone_hash == ph_hash
                )
            )
        except HTTPException:
            user = None

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Patron giriş bilgileri hatalı")

    token = new_session_token()
    db.add(
        AuthSession(
            token=token,
            user_id=user.id,
            principal_type="staff",
            business_id=user.business_id,
        )
    )

    tenant = await db.scalar(select(Tenant).where(Tenant.id == user.business_id))
    business = _tenant_to_dict(tenant) if tenant else None

    return AuthResponse(
        token=token,
        user=_staff_to_public(user, role="owner"),
        business=business,
    )
