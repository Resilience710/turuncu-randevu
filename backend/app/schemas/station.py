"""İstasyon (station) request/response schema'ları."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class StationCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    position: int = Field(default=0, ge=0)


class StationUpdateRequest(BaseModel):
    label: Optional[str] = Field(default=None, min_length=1, max_length=100)
    position: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
