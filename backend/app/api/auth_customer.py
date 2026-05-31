"""Müşteri auth route'ları: request-otp, verify-register, login."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.models.pending_customer import PendingCustomer
from app.models.session import AuthSession
from app.models.user import User
from app.schemas.auth import (
    CustomerLoginRequest,
    CustomerRegisterOtpRequest,
    CustomerVerifyRegisterRequest,
)
from app.schemas.common import AuthResponse, UserPublic
from app.security.otp import generate_otp, hash_otp
from app.security.passwords import hash_password, verify_password
from app.security.phones import (
    encrypt_phone,
    mask_phone,
    normalize_phone,
    phone_hash,
)
from app.security.tokens import new_session_token
from app.sms.netgsm import send_sms

router = APIRouter(prefix="/auth/customer", tags=["auth"])


def _user_to_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        name=f"{user.first_name} {user.last_name}".strip(),
        first_name=user.first_name,
        last_name=user.last_name,
        phone_masked=user.phone_masked,
        gmail=user.gmail,
        role="customer",
    )


async def _ensure_unique_customer(db: AsyncSession, phone_normalized: str, gmail: str) -> None:
    existing = await db.scalar(
        select(User).where(
            or_(User.phone_hash == phone_hash(phone_normalized), User.gmail == gmail)
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Telefon veya Gmail zaten kayıtlı")


@router.post("/request-otp")
async def request_otp(
    payload: CustomerRegisterOtpRequest,
    db: AsyncSession = Depends(get_db),
):
    if not payload.kvkk_accepted:
        raise HTTPException(status_code=400, detail="KVKK onayı olmadan kayıt yapılamaz")

    settings = get_settings()
    normalized = normalize_phone(payload.phone)
    gmail = payload.gmail.lower()

    await _ensure_unique_customer(db, normalized, gmail)

    code = generate_otp()
    ph_hash = phone_hash(normalized)

    # Aynı telefon/gmail için bekleyen kayıtları temizle
    await db.execute(
        delete(PendingCustomer).where(
            or_(PendingCustomer.phone_hash == ph_hash, PendingCustomer.gmail == gmail)
        )
    )

    pending = PendingCustomer(
        id=uuid.uuid4(),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        phone_encrypted=encrypt_phone(normalized),
        phone_hash=ph_hash,
        phone_masked=mask_phone(normalized),
        gmail=gmail,
        password_hash=hash_password(payload.password),
        kvkk_accepted=True,
        otp_hash=hash_otp(normalized, code),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.otp_ttl_seconds),
    )
    db.add(pending)
    await db.flush()

    sms_result = await send_sms(
        db,
        normalized,
        f"Turuncu Randevu doğrulama kodunuz: {code}. "
        f"Kod {settings.otp_ttl_seconds // 60} dakika geçerlidir.",
        "otp",
    )

    response = {
        "status": "otp_sent",
        "expires_in_seconds": settings.otp_ttl_seconds,
        "phone_masked": pending.phone_masked,
    }
    if sms_result.get("status") == "config_missing":
        # Dev/staging için OTP kodu response'a düşer
        response["status"] = "sms_config_missing"
        response["dev_otp_code"] = code
    return response


@router.post("/verify-register", response_model=AuthResponse)
async def verify_register(
    payload: CustomerVerifyRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    normalized = normalize_phone(payload.phone)
    gmail = payload.gmail.lower()
    ph_hash = phone_hash(normalized)

    pending = await db.scalar(
        select(PendingCustomer).where(
            PendingCustomer.phone_hash == ph_hash,
            PendingCustomer.gmail == gmail,
        )
    )
    if not pending or pending.otp_hash != hash_otp(normalized, payload.otp_code):
        raise HTTPException(status_code=400, detail="OTP kodu hatalı")
    if pending.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP süresi doldu")

    await _ensure_unique_customer(db, normalized, gmail)

    user = User(
        id=uuid.uuid4(),
        first_name=pending.first_name,
        last_name=pending.last_name,
        phone_encrypted=pending.phone_encrypted,
        phone_hash=pending.phone_hash,
        phone_masked=pending.phone_masked,
        gmail=pending.gmail,
        password_hash=pending.password_hash,
        phone_verified=True,
        kvkk_accepted_at=datetime.now(timezone.utc),
    )
    db.add(user)

    # Bekleyen kayıt(lar)ı temizle
    await db.execute(
        delete(PendingCustomer).where(PendingCustomer.phone_hash == ph_hash)
    )

    token = new_session_token()
    db.add(
        AuthSession(
            token=token, user_id=user.id, principal_type="customer", business_id=None
        )
    )
    await db.flush()

    return AuthResponse(token=token, user=_user_to_public(user), business=None)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: CustomerLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    normalized = normalize_phone(payload.phone)
    user = await db.scalar(
        select(User).where(
            User.phone_hash == phone_hash(normalized),
            User.gmail == payload.gmail.lower(),
        )
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Müşteri giriş bilgileri hatalı")

    token = new_session_token()
    db.add(
        AuthSession(
            token=token, user_id=user.id, principal_type="customer", business_id=None
        )
    )
    await db.flush()

    return AuthResponse(token=token, user=_user_to_public(user), business=None)
