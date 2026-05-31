"""İşletme (tenant) request/response schema'ları."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ServiceItem(BaseModel):
    id: Optional[uuid.UUID] = None
    name: str = Field(min_length=1, max_length=200)
    duration_minutes: int = Field(default=30, ge=5, le=480)
    price: Optional[Decimal] = None


class BusinessUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    address: Optional[str] = None
    location: Optional[str] = None
    sector: Optional[str] = None
    services: Optional[List[ServiceItem]] = None
    verification_note: Optional[str] = None


class BusinessPublic(BaseModel):
    id: uuid.UUID
    name: str
    sector: str
    sector_label: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
    invite_code: Optional[str] = None
    verification_status: str
    verification_note: Optional[str] = None
    services: List[Dict[str, Any]] = []
    employees: List[Dict[str, Any]] = []
    employee_count: Optional[int] = None
