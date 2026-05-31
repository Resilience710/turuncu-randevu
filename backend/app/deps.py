"""FastAPI dependency'leri: auth, DB session, RLS context."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.session import AuthSession
from app.models.staff_user import StaffUser
from app.models.tenant import Tenant
from app.models.user import User


async def get_current_principal(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Bearer token ile oturum açmış kullanıcıyı döner.

    Hem müşteri (users) hem personel (staff_users) için çalışır.
    Dönen dict: {id, role, business_id, principal_type, name, phone_masked, gmail, ...}
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Oturum gerekli"
        )
    token = authorization.replace("Bearer ", "", 1).strip()

    session_obj = await db.scalar(select(AuthSession).where(AuthSession.token == token))
    if not session_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Oturum bulunamadı"
        )

    if session_obj.principal_type == "customer":
        user = await db.scalar(select(User).where(User.id == session_obj.user_id))
        if not user:
            raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı")
        return {
            "id": user.id,
            "principal_type": "customer",
            "role": "customer",
            "business_id": None,
            "name": f"{user.first_name} {user.last_name}".strip(),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_masked": user.phone_masked,
            "gmail": user.gmail,
            "title": None,
            "station": None,
        }
    else:
        staff = await db.scalar(
            select(StaffUser).where(StaffUser.id == session_obj.user_id)
        )
        if not staff:
            raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı")
        return {
            "id": staff.id,
            "principal_type": "staff",
            "role": staff.role,
            "business_id": staff.business_id,
            "name": staff.name,
            "first_name": staff.first_name,
            "last_name": staff.last_name,
            "phone_masked": staff.phone_masked,
            "gmail": staff.gmail,
            "title": staff.title,
            "station": staff.station_label,
        }


async def set_rls_context(
    db: AsyncSession,
    principal: Dict[str, Any],
) -> None:
    """Her tenant-scoped istekte RLS GUC'ları set'ler.

    Faz 2'de RLS politikaları açılacak; o ana kadar bu çağrı no-op gibi çalışır
    çünkü politikalar henüz yok. set_config ile boş policy ortamında da safe.
    """
    business_id = principal.get("business_id")
    user_id = principal.get("id")
    role = principal.get("role") or "anon"
    # 3 set_config'i tek round-trip'te çalıştır (uzak DB'de gecikmeyi azaltır)
    await db.execute(
        text(
            "SELECT set_config('app.current_business_id', :bid, true), "
            "set_config('app.current_user_id', :uid, true), "
            "set_config('app.current_role', :role, true)"
        ),
        {
            "bid": str(business_id) if business_id else "",
            "uid": str(user_id) if user_id else "",
            "role": role,
        },
    )


async def require_owner(
    principal: Dict[str, Any] = Depends(get_current_principal),
) -> Dict[str, Any]:
    if principal.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Bu işlem için işletme sahibi olunmalı")
    return principal


async def require_staff_or_owner(
    principal: Dict[str, Any] = Depends(get_current_principal),
) -> Dict[str, Any]:
    if principal.get("role") not in ("owner", "staff"):
        raise HTTPException(status_code=403, detail="Bu işlem için personel olunmalı")
    return principal


async def tenant_business(
    db: AsyncSession, business_id) -> Optional[Tenant]:
    return await db.scalar(select(Tenant).where(Tenant.id == business_id))
