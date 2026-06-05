"""E-posta gönderimi (SMTP / Gmail).

SMS'in yaptığı tüm işlerin (OTP doğrulama, randevu onayı, hatırlatma) yeni
kanalı. Gmail App Password ile smtp.gmail.com:587 üzerinden STARTTLS.

Config eksikse (smtp_user/smtp_password boş) status='config_missing' döner —
dev'de akış kırılmaz, OTP response'a düşer (ekranda gösterilir).

NOT: Bu paket 'mail' adında; stdlib 'email' modülünü gölgelememesi için
bilerek böyle adlandırıldı (içeride `from email.message import ...` çalışır).
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any, Dict, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


def _mask_email(addr: str) -> str:
    try:
        local, domain = addr.split("@", 1)
        if len(local) <= 2:
            masked = (local[:1] or "*") + "*"
        else:
            masked = local[0] + "*" * (len(local) - 2) + local[-1]
        return f"{masked}@{domain}"
    except ValueError:
        return "***"


def _send_sync(
    host: str,
    port: int,
    user: str,
    password: str,
    use_tls: bool,
    msg: EmailMessage,
) -> None:
    context = ssl.create_default_context()
    if use_tls:
        # 587 / STARTTLS (Gmail varsayılanı)
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(user, password)
            server.send_message(msg)
    else:
        # 465 / SSL
        with smtplib.SMTP_SSL(host, port, timeout=20, context=context) as server:
            server.login(user, password)
            server.send_message(msg)


async def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    purpose: str = "general",
) -> Dict[str, Any]:
    """Tek bir e-posta gönderir.

    Returns: {"sent": bool, "status": "sent"|"failed"|"config_missing"}
    """
    settings = get_settings()
    user = settings.smtp_user.strip()
    password = settings.smtp_password.strip()

    if not user or not password:
        logger.info("E-posta config eksik (purpose=%s) — gönderilmedi", purpose)
        return {"sent": False, "status": "config_missing"}

    from_email = (settings.smtp_from_email or user).strip()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.smtp_from_name, from_email))
    msg["To"] = to_email
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    try:
        await asyncio.to_thread(
            _send_sync,
            settings.smtp_host,
            settings.smtp_port,
            user,
            password,
            settings.smtp_use_tls,
            msg,
        )
        logger.info(
            "E-posta gönderildi (purpose=%s, to=%s)", purpose, _mask_email(to_email)
        )
        return {"sent": True, "status": "sent"}
    except Exception as exc:  # noqa: BLE001 — tüm SMTP hatalarını yut, akışı kırma
        logger.warning("E-posta gönderilemedi (purpose=%s): %s", purpose, exc)
        return {"sent": False, "status": "failed", "error": str(exc)}


# --- Şablonlar -------------------------------------------------------------

_BRAND = "#F97316"


def _wrap_html(title: str, inner_html: str) -> str:
    return f"""\
<!doctype html>
<html lang="tr"><head><meta charset="utf-8"></head>
<body style="margin:0;background:#f1f5f9;padding:24px;font-family:Segoe UI,Inter,Arial,sans-serif;color:#0f172a;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:460px;margin:0 auto;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #e2e8f0;">
    <tr><td style="background:{_BRAND};padding:20px 28px;">
      <span style="color:#ffffff;font-size:18px;font-weight:700;">Turuncu Randevu</span>
    </td></tr>
    <tr><td style="padding:28px;">
      <h1 style="margin:0 0 12px;font-size:20px;font-weight:700;">{title}</h1>
      {inner_html}
    </td></tr>
    <tr><td style="padding:16px 28px;border-top:1px solid #e2e8f0;color:#94a3b8;font-size:12px;">
      Bu e-posta Turuncu Randevu tarafından gönderildi. Bu işlemi siz başlatmadıysanız dikkate almayın.
    </td></tr>
  </table>
</body></html>"""


def build_otp_email(code: str, ttl_minutes: int) -> tuple[str, str]:
    """OTP doğrulama e-postası — (düz metin, html) döner."""
    text = (
        f"Turuncu Randevu doğrulama kodunuz: {code}\n"
        f"Kod {ttl_minutes} dakika geçerlidir.\n\n"
        "Bu işlemi siz başlatmadıysanız bu e-postayı dikkate almayın."
    )
    inner = f"""\
      <p style="margin:0 0 16px;font-size:14px;color:#475569;">Hesabını doğrulamak için aşağıdaki kodu gir:</p>
      <div style="text-align:center;margin:8px 0 18px;">
        <span style="display:inline-block;background:#fff7ed;border:1px solid {_BRAND};color:#ea580c;
          font-size:30px;font-weight:700;letter-spacing:8px;padding:14px 22px;border-radius:12px;">{code}</span>
      </div>
      <p style="margin:0;font-size:13px;color:#94a3b8;">Kod {ttl_minutes} dakika geçerlidir.</p>"""
    return text, _wrap_html("Doğrulama kodun", inner)


def build_confirm_email(
    business_name: str, date_iso: str, time_str: str, service_name: str
) -> tuple[str, str]:
    """Randevu onayı e-postası — (düz metin, html) döner."""
    text = (
        f"{business_name} için randevunuz onaylandı.\n"
        f"Tarih: {date_iso}  Saat: {time_str}\n"
        f"Hizmet: {service_name}\n\n"
        "Randevudan 15 dakika önce hatırlatma e-postası göndereceğiz."
    )
    inner = f"""\
      <p style="margin:0 0 16px;font-size:14px;color:#475569;">
        <strong>{business_name}</strong> için randevunuz oluşturuldu.</p>
      <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;font-size:14px;">
        <tr><td style="padding:6px 0;color:#94a3b8;width:90px;">Tarih</td><td style="padding:6px 0;font-weight:600;">{date_iso}</td></tr>
        <tr><td style="padding:6px 0;color:#94a3b8;">Saat</td><td style="padding:6px 0;font-weight:600;">{time_str}</td></tr>
        <tr><td style="padding:6px 0;color:#94a3b8;">Hizmet</td><td style="padding:6px 0;font-weight:600;">{service_name}</td></tr>
      </table>
      <p style="margin:16px 0 0;font-size:13px;color:#94a3b8;">Randevudan 15 dakika önce hatırlatma göndereceğiz.</p>"""
    return text, _wrap_html("Randevunuz onaylandı", inner)
