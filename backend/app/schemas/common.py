"""Ortak Pydantic schema'ları."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, EmailStr


class UserPublic(BaseModel):
    id: uuid.UUID
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_masked: Optional[str] = None
    gmail: Optional[EmailStr] = None
    role: Literal["customer", "owner", "staff"]
    business_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    station: Optional[str] = None


class AuthResponse(BaseModel):
    token: str
    user: UserPublic
    business: Optional[Dict[str, Any]] = None


class SectorPublic(BaseModel):
    id: str
    label: str
    icon: str


class OkResponse(BaseModel):
    ok: bool = True
