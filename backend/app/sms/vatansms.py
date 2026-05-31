"""VatanSMS (REST API v1) entegrasyonu.

Resmi SDK kontratına (vatanyazilim/vatansmsnet-php & -dotnet) birebir uygundur:
  POST  {base_url}/1toN
  Header: Content-Type: application/json
  Body:  api_id, api_key, sender, message_type, message,
         message_content_type, phones[], (opsiyonel) send_time
  Telefon formatı: "5XXXXXXXXX" (10 hane, başında 0 yok, ülke kodu yok)
  Başarı: HTTP 2xx

Tüm SMS gönderimleri (OTP, randevu onayı, hatırlatma) bu fonksiyondan geçer.
Config eksikse status='config_missing' döner — dev'de akış kırılmaz (OTP ekrana düşer).
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


def to_vatansms_phone(phone: str) -> str:
    """Telefonu VatanSMS formatına çevirir: 10 hane, '5' ile başlar, 0/90 yok.

    normalize_phone '90' + 10 hane döndürür (örn. '905321234567').
    VatanSMS '5321234567' ister.
    """
    digits = "".join(ch for ch in normalize_phone(phone) if ch.isdigit())
    if digits.startswith("90") and len(digits) == 12:
        return digits[2:]
    if len(digits) == 10:
        return digits
    return digits[-10:]


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

    api_id = settings.vatansms_api_id
    api_key = settings.vatansms_api_key
    sender = settings.vatansms_sender

    if not api_id or not api_key or not sender:
        log.status = "config_missing"
        db.add(log)
        await db.flush()
        return {"sent": False, "status": "config_missing"}

    url = settings.vatansms_base_url.rstrip("/") + "/1toN"
    payload = {
        "api_id": api_id,
        "api_key": api_key,
        "sender": sender,
        "message_type": settings.vatansms_message_type or "normal",
        "message": message,
        "message_content_type": settings.vatansms_content_type or "bilgi",
        "phones": [to_vatansms_phone(normalized)],
    }

    try:
        response = await asyncio.to_thread(
            requests.post,
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        # ÖNEMLİ: VatanSMS hata durumunda bile HTTP 200 döner; gerçek sonucu
        # gövdedeki "status"/"code" alanları belirler.
        # Başarı:  {"status":"success","code":200,...}
        # Hata:    {"status":"error","code":400,"description":"..."}
        ok = False
        desc = ""
        try:
            body = response.json()
            status_field = str(body.get("status", "")).lower()
            code_field = body.get("code")
            ok = response.ok and (
                status_field == "success" or str(code_field) == "200"
            )
            desc = str(body.get("description") or body.get("message") or "")
        except ValueError:
            # JSON değilse HTTP koduna düş
            ok = response.ok

        log.provider_response = response.text[:300]
        log.status = "sent" if ok else "failed"
        if not ok and desc:
            log.error = desc
        db.add(log)
        await db.flush()
        return {
            "sent": ok,
            "status": log.status,
            "provider_response": (desc or response.text[:120]),
        }
    except Exception as exc:
        log.status = "failed"
        log.error = str(exc)
        db.add(log)
        await db.flush()
        return {"sent": False, "status": "failed"}
