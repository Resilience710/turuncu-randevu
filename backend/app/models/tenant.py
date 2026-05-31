"""Tenant (işletme) tablosu — multi-tenant kök varlık."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sector_id: Mapped[str] = mapped_column(
        ForeignKey("sectors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    invite_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    verification_status: Mapped[str] = mapped_column(
        String(20), default="beklemede", nullable=False
    )
    verification_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kvkk_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
