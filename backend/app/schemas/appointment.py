"""Randevu request/response schema'ları."""

from __future__ import annotations

import uuid
from datetime import date as _date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class AppointmentCreateRequest(BaseModel):
    business_id: uuid.UUID
    staff_id: uuid.UUID
    service_id: Optional[uuid.UUID] = None
    service_name: str = Field(min_length=1, max_length=200)
    date: _date
    time: str = Field(pattern=r"^\d{2}:\d{2}$")  # "HH:MM"
    station_id: Optional[uuid.UUID] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    source: Optional[Literal["customer", "manual"]] = "customer"


class CancelRequest(BaseModel):
    reason: Optional[str] = None
