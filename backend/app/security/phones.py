"""KVKK uyumlu telefon işlemleri: normalize, mask, hash, AES-256-GCM encrypt/decrypt.

Eski server.py:80-134'ten port.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException

from app.config import get_settings

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    """Türk telefon numarasını 90XXXXXXXXXX formatına dönüştürür."""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if digits.startswith("90") and len(digits) == 12:
        return digits
    if digits.startswith("0") and len(digits) == 11:
        return f"90{digits[1:]}"
    if digits.startswith("0"):
        raise HTTPException(status_code=400, detail="Telefon 05xx xxx xx xx formatında olmalı")
    if len(digits) == 10:
        return f"90{digits}"
    if len(digits) >= 10:
        return digits
    raise HTTPException(status_code=400, detail="Geçerli telefon numarası girin")


def mask_phone(phone: str) -> str:
    """Görüntüleme için: 0532 *** 12 34"""
    normalized = normalize_phone(phone)
    local = "0" + normalized[-10:]
    return f"{local[:4]} *** {local[-4:-2]} {local[-2:]}"


def phone_hash(phone: str) -> bytes:
    """Arama için: peppered SHA-256. bytea olarak saklanır."""
    settings = get_settings()
    pepper = settings.phone_hash_pepper or settings.phone_encryption_key or settings.database_url
    return hashlib.sha256(f"{normalize_phone(phone)}:{pepper}".encode()).digest()


def _get_phone_key() -> bytes:
    """AES-256 anahtarını çıkarır (32 byte)."""
    settings = get_settings()
    raw = settings.phone_encryption_key
    if raw:
        try:
            decoded = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
            if len(decoded) >= 32:
                return decoded[:32]
        except Exception:
            pass
        if len(raw.encode()) >= 32:
            return raw.encode()[:32]
    logger.warning("PHONE_ENCRYPTION_KEY eksik; geliştirme anahtarı kullanılıyor")
    return hashlib.sha256(f"{settings.database_url}:phone-dev-fallback".encode()).digest()


def encrypt_phone(phone: str) -> bytes:
    """Telefonu AES-GCM ile şifreler. nonce(12) || ciphertext döner. bytea olarak saklanır."""
    aes = AESGCM(_get_phone_key())
    nonce = secrets.token_bytes(12)
    encrypted = aes.encrypt(nonce, normalize_phone(phone).encode(), None)
    return nonce + encrypted


def decrypt_phone(ciphertext: bytes | None) -> str:
    """Şifreli telefonu çözer. Hata varsa boş string döner (eski koddaki davranışla aynı)."""
    if not ciphertext:
        return ""
    try:
        nonce, encrypted = ciphertext[:12], ciphertext[12:]
        return AESGCM(_get_phone_key()).decrypt(nonce, encrypted, None).decode()
    except Exception:
        return ""
