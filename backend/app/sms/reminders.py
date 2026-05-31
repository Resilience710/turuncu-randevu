"""SMS hatırlatma worker'ı.

Backend lifespan startup'ında asyncio.create_task ile çalıştırılır.
Her 60 saniyede bir sms_reminders tablosundan `send_at <= now` ve status'ü
'pending'/'due' olanları çeker, Netgsm'e gönderir.

Eski server.py:787-819'daki reminder_worker'ın SQLAlchemy portu.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.sms_reminder import SmsReminder
from app.security.phones import decrypt_phone
from app.sms.vatansms import send_sms

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 60
BATCH_SIZE = 20


async def _process_batch(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    due = (
        await db.scalars(
            select(SmsReminder)
            .where(
                SmsReminder.status.in_(("pending", "due")),
                SmsReminder.send_at <= now,
            )
            .order_by(SmsReminder.send_at)
            .limit(BATCH_SIZE)
        )
    ).all()

    processed = 0
    for reminder in due:
        phone = decrypt_phone(reminder.phone_encrypted)
        if not phone:
            reminder.status = "missing_phone"
            reminder.processed_at = datetime.now(timezone.utc)
            continue
        result = await send_sms(db, phone, reminder.message, "appointment_reminder")
        reminder.status = "sent" if result.get("sent") else result.get("status", "failed")
        reminder.processed_at = datetime.now(timezone.utc)
        processed += 1
    return processed


async def reminder_worker() -> None:
    """Sonsuz döngü; uygulama kapanana kadar çalışır."""
    logger.info("SMS reminder worker başladı (her %s sn)", POLL_INTERVAL_SECONDS)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                try:
                    count = await _process_batch(db)
                    if count:
                        logger.info("SMS reminder: %s adet gönderildi", count)
                    await db.commit()
                except Exception:
                    await db.rollback()
                    raise
        except Exception as exc:
            logger.warning("Reminder worker hatası: %s", exc)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
