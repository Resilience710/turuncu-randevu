"""Netgsm SMS sağlayıcısı entegrasyonu. Eski server.py:145-182'den port.

Tüm SMS gönderimleri (OTP, randevu onayı, hatırlatma) bu fonksiyondan geçer.
Config eksikse status='config_missing' döner — dev ortamında akış kırılmaz.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict

import requests
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.sms_log import SmsLog
from app.security.phones import mask_phone, normalize_phone, phone_hash

logger = logging.getLogger(__name__)


async def send_sms(
    db: AsyncSession,
    phone: str,
    message: str,
    purpose: str = "general",
) -> Dict[str, Any]:
    """Tek bir SMS gönderir ve sms_logs'a kaydeder.

    Returns: {"sent": bool, "status": str, "provider_response": str?}
    """
    normalized = normalize_phone(phone)
    settings = get_settings()

    log = SmsLog(
        id=uuid.uuid4(),
        phone_hash=phone_hash(normalized),
        phone_masked=mask_phone(normalized),
        message=message,
        purpose=purpose,
        status="pending",
    )

    usercode = settings.netgsm_usercode
    password = settings.netgsm_password
    msgheader = settings.netgsm_msgheader

    if not usercode or not password or not msgheader:
        log.status = "config_missing"
        db.add(log)
        await db.flush()
        return {"sent": False, "status": "config_missing"}

    params = {
        "usercode": usercode,
        "password": password,
        "gsmno": normalized,
        "message": message,
        "msgheader": msgheader,
        "dil": "TR",
    }
    try:
        response = await asyncio.to_thread(
            requests.get, settings.netgsm_api_url, params=params, timeout=12
        )
        log.provider_response = response.text[:300]
        log.status = "sent" if response.ok else "failed"
        db.add(log)
        await db.flush()
        return {
            "sent": response.ok,
            "status": log.status,
            "provider_response": response.text[:80],
        }
    except Exception as exc:
        log.status = "failed"
        log.error = str(exc)
        db.add(log)
        await db.flush()
        return {"sent": False, "status": "failed"}
