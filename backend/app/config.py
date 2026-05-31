"""Çevre değişkenlerini yükler ve doğrular (pydantic-settings)."""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Veritabanı
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/turuncu",
        description="SQLAlchemy async DSN",
    )

    # KVKK / şifreleme
    phone_encryption_key: str = Field(
        default="",
        description="AES-256 anahtarı (32 byte, base64url). Boşsa dev fallback (güvensiz).",
    )
    phone_hash_pepper: str = Field(default="", description="Telefon hash pepper'ı")
    otp_secret: str = Field(default="", description="OTP hash secret'ı")
    otp_ttl_seconds: int = Field(default=300, ge=60, le=3600)

    # Netgsm
    netgsm_usercode: str = ""
    netgsm_password: str = ""
    netgsm_msgheader: str = ""
    netgsm_api_url: str = "https://api.netgsm.com.tr/sms/send/get/"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Uygulama
    app_env: str = "development"
    log_level: str = "INFO"

    @field_validator("database_url")
    @classmethod
    def _ensure_async_driver(cls, v: str) -> str:
        # asyncpg sürücüsünü zorla
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in ("production", "prod")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
