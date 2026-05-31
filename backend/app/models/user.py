"""Müşteri (customer) tablosu. Telefonlar AES-GCM ile şifreli saklanır."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # KVKK: telefon ciphertext (nonce||ct), arama için ayrı hash
    phone_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    phone_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    phone_masked: Mapped[str] = mapped_column(String(30), nullable=False)
    gmail: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    kvkk_accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_users_phone_hash", "phone_hash", unique=True),
        Index("ix_users_gmail", "gmail", unique=True),
    )
