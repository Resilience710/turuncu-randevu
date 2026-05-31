"""GET /api/me — mevcut oturum bilgisi."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_principal
from app.models.tenant import Tenant
from app.schemas.common import AuthResponse, UserPublic

router = APIRouter(tags=["auth"])


@router.get("/me", response_model=AuthResponse)
async def me(
    principal: Dict[str, Any] = Depends(get_current_principal),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    business = None
    if principal.get("business_id"):
        tenant = await db.scalar(
            select(Tenant).where(Tenant.id == principal["business_id"])
        )
        if tenant:
            business = {
                "id": str(tenant.id),
                "name": tenant.name,
                "sector": tenant.sector_id,
                "address": tenant.address,
                "location": tenant.location,
                "invite_code": tenant.invite_code,
                "verification_status": tenant.verification_status,
            }

    user_public = UserPublic(
        id=principal["id"],
        name=principal["name"],
        first_name=principal.get("first_name"),
        last_name=principal.get("last_name"),
        phone_masked=principal.get("phone_masked"),
        gmail=principal.get("gmail"),
        role=principal["role"],
        business_id=principal.get("business_id"),
        title=principal.get("title"),
        station=principal.get("station"),
    )
    token = (authorization or "").replace("Bearer ", "", 1).strip()
    return AuthResponse(token=token, user=user_public, business=business)
