"""Oturum token'ları ve davet kodu üretimi."""

from __future__ import annotations

import secrets


def new_session_token() -> str:
    """URL-safe 32 byte rastgele oturum token'ı."""
    return secrets.token_urlsafe(32)


def new_invite_code() -> str:
    """İşletme davet kodu (6 hex char, uppercase)."""
    return secrets.token_hex(3).upper()
