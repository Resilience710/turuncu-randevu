"""SQLAlchemy DeclarativeBase — sadece sınıf tanımı (circular import'u önler)."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Tüm ORM modellerinin ortak tabanı."""
    pass
