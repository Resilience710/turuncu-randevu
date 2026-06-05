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

    # --- E-posta gönderimi ---
    # ÖNCELİK: brevo_api_key doluysa Brevo HTTP API (port 443) kullanılır.
    # Bunun sebebi: Render ücretsiz plan giden SMTP portlarını (25/465/587)
    # engelliyor → Gmail SMTP production'da çalışmaz. Brevo HTTPS üzerinden
    # gönderir, engellenmez. Lokal dev'de brevo boşsa SMTP fallback devreye girer.
    # Gönderen adresi her iki yolda da smtp_from_email/smtp_user'dan alınır.
    brevo_api_key: str = ""

    # SMTP (lokal dev / paid plan fallback). Gmail: smtp.gmail.com:587,
    # smtp_password = Google App Password (16 hane).
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""          # gönderen gmail adresi
    smtp_password: str = ""      # Gmail App Password (boşluksuz 16 hane)
    smtp_from_email: str = ""    # boşsa smtp_user kullanılır
    smtp_from_name: str = "Turuncu Randevu"
    smtp_use_tls: bool = True    # 587/STARTTLS. SSL (465) için False yap.

    # VatanSMS (REST API v1) — ŞU AN PASİF. Kod kenarda duruyor; çağrılmıyor.
    # Tekrar SMS'e dönülmek istenirse bu değerler doldurulup ilgili import'lar
    # app.sms.vatansms'e geri çevrilir.
    vatansms_api_id: str = ""
    vatansms_api_key: str = ""
    vatansms_sender: str = ""  # bireysel: 0850'li abone numarası, kurumsal: onaylı başlık
    vatansms_base_url: str = "https://api.vatansms.net/api/v1"
    vatansms_message_type: str = "normal"  # "normal" (ASCII'ye çevirir, 1 SMS) | "turkce"
    vatansms_content_type: str = "bilgi"   # işlemsel/bilgilendirme (İYS dışı)

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

    @property
    def email_configured(self) -> bool:
        return bool(self.brevo_api_key or (self.smtp_user and self.smtp_password))

    @property
    def sender_email(self) -> str:
        return (self.smtp_from_email or self.smtp_user or "").strip()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
