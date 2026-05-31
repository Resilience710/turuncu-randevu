"""Alembic metadata için tüm modelleri yan etkiyle import eden modül."""

from __future__ import annotations

from app.db.base_class import Base  # noqa: F401

# Yan etki: modellerin tabloları Base.metadata'ya kaydolur
from app.models import (  # noqa: E402,F401
    sector,
    tenant,
    user,
    staff_user,
    station,
    service,
    appointment,
    appointment_event,
    session,
    pending_customer,
    sms_log,
    sms_reminder,
)
