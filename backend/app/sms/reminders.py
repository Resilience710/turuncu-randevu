"""Randevu hatırlatma worker'ı (e-posta).

Backend lifespan startup'ında asyncio.create_task ile çalıştırılır.
Her 60 saniyede bir sms_reminders kuyruğundan `send_at <= now` ve status'ü
'pending'/'due' olanları çeker, alıcıya hatırlatma e-postası gönderir.

NOT: Tablo adı tarihsel sebeple 'sms_reminders'; içerik artık e-posta ile
gider (recipient_email alanı). SMS kodu kenarda/pasif.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.mail.mailer import send_email
from app.models.sms_reminder import SmsReminder

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
        if not reminder.recipient_email:
            reminder.status = "missing_email"
            reminder.processed_at = datetime.now(timezone.utc)
            continue
        result = await send_email(
            reminder.recipient_email,
            "Randevu hatırlatma — Turuncu Randevu",
            reminder.message,
            None,
            "appointment_reminder",
        )
        reminder.status = "sent" if result.get("sent") else result.get("status", "failed")
        reminder.processed_at = datetime.now(timezone.utc)
        processed += 1
    return processed


async def reminder_worker() -> None:
    """Sonsuz döngü; uygulama kapanana kadar çalışır."""
    logger.info("Hatırlatma worker başladı (e-posta, her %s sn)", POLL_INTERVAL_SECONDS)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                try:
                    count = await _process_batch(db)
                    if count:
                        logger.info("Hatırlatma: %s e-posta gönderildi", count)
                    await db.commit()
                except Exception:
                    await db.rollback()
                    raise
        except Exception as exc:
            logger.warning("Reminder worker hatası: %s", exc)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
