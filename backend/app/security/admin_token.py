"""Admin paneli için stateless imzalı token (HMAC-SHA256).

sessions tablosu customer/staff'a kısıtlı olduğu için admin oturumunu DB'ye
yazmıyoruz; token kendi içinde imzalı ve süreli. Anahtar = otp_secret + admin
şifresi → şifre değişince eski token'lar geçersiz olur.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from app.config import get_settings

TOKEN_TTL_SECONDS = 24 * 60 * 60  # 24 saat


def _key() -> bytes:
    s = get_settings()
    return (s.otp_secret + "|admin|" + s.admin_password).encode("utf-8")


def make_admin_token() -> str:
    payload = {"r": "admin", "iat": int(time.time())}
    raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = hmac.new(_key(), raw.encode(), hashlib.sha256).hexdigest()
    return raw + "." + sig


def verify_admin_token(token: str, max_age: int = TOKEN_TTL_SECONDS) -> bool:
    if not token or "." not in token:
        return False
    raw, _, sig = token.rpartition(".")
    expected = hmac.new(_key(), raw.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        pad = "=" * (-len(raw) % 4)
        payload = json.loads(base64.urlsafe_b64decode(raw + pad))
    except Exception:
        return False
    if payload.get("r") != "admin":
        return False
    if int(time.time()) - int(payload.get("iat", 0)) > max_age:
        return False
    return True
