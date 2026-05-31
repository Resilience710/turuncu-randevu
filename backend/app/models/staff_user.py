"""Patron + personel ortak tablosu (role kolonuyla ayrılır)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class StaffUser(Base):
    __tablename__ = "staff_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'owner' | 'staff'
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    phone_hash: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    phone_masked: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    gmail: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # İleride normalleştirilmiş stations tablosuna FK olabilir (Faz 3'te eklenir)
    station_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    station_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Çoklu istasyon ataması (atanabilir tüm istasyonların id'leri, string listesi)
    station_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("role IN ('owner','staff')", name="ck_staff_role"),
        Index("ix_staff_business_role", "business_id", "role"),
        Index("ix_staff_phone_hash", "phone_hash"),
        Index("ix_staff_gmail", "gmail"),
    )
