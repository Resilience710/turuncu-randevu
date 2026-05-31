"""PBKDF2-SHA256 şifre hash'leme. Eski server.py:66-77'den port."""

from __future__ import annotations

import hashlib
import secrets
from typing import Optional


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _, salt, _ = password_hash.split("$", 2)
        return secrets.compare_digest(hash_password(password, salt), password_hash)
    except ValueError:
        return False
