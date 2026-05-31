"""Çalışan (staff_users) request schema'ları."""

from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.auth import validate_strong_password


class EmployeeCreateRequest(BaseModel):
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    password: str = Field(min_length=8, max_length=128)
    title: Optional[str] = "Çalışan"
    station: Optional[str] = None  # geriye dönük; artık station_ids tercih edilir
    station_ids: List[uuid.UUID] = Field(default_factory=list)

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return validate_strong_password(v)
