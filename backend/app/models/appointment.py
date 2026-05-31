"""Randevu tablosu. Unique partial index slot çakışmasını DB seviyesinde garanti eder."""

from __future__ import annotations

import uuid
from datetime import date as _date, datetime, time as _time
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    Time,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("staff_users.id", ondelete="RESTRICT"), nullable=False
    )
    station_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("stations.id", ondelete="SET NULL"), nullable=True
    )
    service_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("services.id", ondelete="SET NULL"), nullable=True
    )
    service_name: Mapped[str] = mapped_column(String(200), nullable=False)
    date: Mapped[_date] = mapped_column(Date, nullable=False)
    time: Mapped[_time] = mapped_column(Time, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="booked", nullable=False)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    customer_phone_encrypted: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary, nullable=True
    )
    customer_phone_masked: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="customer", nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('booked','in_service','done','cancelled','no_show')",
            name="ck_appt_status",
        ),
        CheckConstraint("source IN ('customer','manual')", name="ck_appt_source"),
        # Aktif randevular arasında slot tekil — slot çakışmasını DB garanti eder
        Index(
            "uq_appt_active_slot",
            "business_id",
            "staff_id",
            "date",
            "time",
            unique=True,
            postgresql_where=text("status IN ('booked','in_service')"),
        ),
        Index("ix_appt_business_date", "business_id", "date"),
        Index("ix_appt_staff_status", "staff_id", "status"),
        Index("ix_appt_customer", "customer_id"),
    )
