"""SMS OTP üretimi ve hash'leme. Eski server.py:137-142'den port."""

from __future__ import annotations

import hashlib
import secrets
import string

from app.config import get_settings
from app.security.phones import normalize_phone


def generate_otp() -> str:
    """6 haneli sayısal OTP üretir."""
    return "".join(secrets.choice(string.digits) for _ in range(6))


def hash_otp(phone: str, code: str) -> str:
    """OTP'yi telefon + secret ile peppered SHA-256 olarak hash'ler."""
    settings = get_settings()
    secret = settings.otp_secret or settings.database_url
    return hashlib.sha256(
        f"{normalize_phone(phone)}:{code}:{secret}".encode()
    ).hexdigest()
