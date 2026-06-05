"""Randevu route'ları: create (customer+manual), list, cancel, delete, export.

Status transitions (start/finish) Faz 5'te eklenir.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time as _time, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import (
    get_current_principal,
    require_owner,
    require_staff_or_owner,
    set_rls_context,
)
from app.models.appointment import Appointment
from app.models.appointment_event import AppointmentEvent
from app.models.staff_user import StaffUser
from app.models.tenant import Tenant
from app.schemas.appointment import AppointmentCreateRequest, CancelRequest
from app.security.phones import (
    decrypt_phone,
    encrypt_phone,
    mask_phone,
    normalize_phone,
)
from app.services.slots import make_slots
from app.mail.mailer import build_confirm_email, send_email

router = APIRouter(tags=["appointments"])


def _appt_public(a: Appointment) -> Dict[str, Any]:
    return {
        "id": str(a.id),
        "business_id": str(a.business_id),
        "staff_id": str(a.staff_id),
        "station_id": str(a.station_id) if a.station_id else None,
        "service_id": str(a.service_id) if a.service_id else None,
        "service_name": a.service_name,
        "date": a.date.isoformat(),
        "time": a.time.strftime("%H:%M"),
        "status": a.status,
        "customer_id": str(a.customer_id) if a.customer_id else None,
        "customer_name": a.customer_name,
        "customer_phone_masked": a.customer_phone_masked,
        "source": a.source,
        "started_at": a.started_at.isoformat() if a.started_at else None,
        "finished_at": a.finished_at.isoformat() if a.finished_at else None,
        "cancelled_at": a.cancelled_at.isoformat() if a.cancelled_at else None,
        "cancel_reason": a.cancel_reason,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.post("/appointments")
async def create_appointment(
    payload: AppointmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    principal: Dict[str, Any] = Depends(get_current_principal),
):
    if payload.time not in make_slots():
        raise HTTPException(status_code=400, detail="Geçersiz saat")

    business = await db.scalar(select(Tenant).where(Tenant.id == payload.business_id))
    staff = await db.scalar(
        select(StaffUser).where(
            StaffUser.id == payload.staff_id,
            StaffUser.business_id == payload.business_id,
        )
    )
    if not business or not staff:
        raise HTTPException(status_code=404, detail="İşletme veya çalışan bulunamadı")

    role = principal.get("role")
    if role == "customer":
        customer_id = principal["id"]
        customer_name = principal["name"]
        # Müşteri kendi şifreli telefonunu çözüp randevuya kopyalar
        from app.models.user import User as CustomerUser

        cust = await db.scalar(select(CustomerUser).where(CustomerUser.id == customer_id))
        customer_phone = decrypt_phone(cust.phone_encrypted) if cust else ""
        customer_email = cust.gmail if cust else None
        source = "customer"
    else:
        if principal.get("business_id") != payload.business_id:
            raise HTTPException(status_code=403, detail="Bu işletme için yetkiniz yok")
        await set_rls_context(db, principal)
        customer_id = None
        customer_name = payload.customer_name or "Telefon müşterisi"
        customer_phone = payload.customer_phone or ""
        customer_email = None  # manuel/telefon müşterisinin e-postası yok
        source = payload.source or "manual"
        if source == "customer":
            source = "manual"  # staff oluşturduysa override

    # Müşterinin manual oluşturduğu randevuda RLS context gerekmez (tenants public)
    # ama appointments tablosunda RLS açık — customer self policy SELECT için.
    # INSERT için business_id eşleşmesi gerekiyor; bu yüzden müşteri için de
    # RLS context'i set'liyoruz ki WITH CHECK pass etsin.
    if role == "customer":
        # Customer için RLS GUC'ları tek round-trip'te set et
        from sqlalchemy import text as _text

        await db.execute(
            _text(
                "SELECT set_config('app.current_business_id', :bid, true), "
                "set_config('app.current_user_id', :uid, true), "
                "set_config('app.current_role', :r, true)"
            ),
            {"bid": str(payload.business_id), "uid": str(customer_id), "r": "customer"},
        )

    customer_phone_enc = encrypt_phone(customer_phone) if customer_phone else None
    customer_phone_msk = mask_phone(customer_phone) if customer_phone else None

    # Randevuyu bir istasyona bağla: önce payload, sonra personelin primary
    # istasyonu, o da yoksa personele atanmış ilk istasyon.
    station_id = payload.station_id or staff.station_id
    if station_id is None and staff.station_ids:
        try:
            station_id = uuid.UUID(str(staff.station_ids[0]))
        except (ValueError, TypeError, IndexError):
            station_id = None

    appt = Appointment(
        id=uuid.uuid4(),
        business_id=payload.business_id,
        staff_id=payload.staff_id,
        station_id=station_id,
        service_id=payload.service_id,
        service_name=payload.service_name,
        date=payload.date,
        time=_time.fromisoformat(payload.time),
        status="booked",
        customer_id=customer_id,
        customer_name=customer_name,
        customer_phone_encrypted=customer_phone_enc,
        customer_phone_masked=customer_phone_msk,
        source=source,
        created_by=principal["id"],
    )
    db.add(appt)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="Bu saat dolu, lütfen başka saat seçin"
        )

    # Audit event
    db.add(
        AppointmentEvent(
            id=uuid.uuid4(),
            appointment_id=appt.id,
            event_type="created",
            actor_id=principal["id"],
            actor_role=role,
        )
    )

    # E-posta onayı + hatırlatma (yalnız e-postası olan kayıtlı müşteriler).
    # Manuel/telefon müşterisinin e-postası yoktur → bildirim atlanır.
    if customer_email:
        confirm_text, confirm_html = build_confirm_email(
            business.name, payload.date.isoformat(), payload.time, appt.service_name
        )
        await send_email(
            customer_email,
            f"Randevunuz onaylandı — {business.name}",
            confirm_text,
            confirm_html,
            "appointment_confirm",
        )
        # 15 dk öncesi hatırlatma için kuyruğa ekle (reminder_worker tüketir)
        await _schedule_reminder(db, appt, customer_email, customer_phone)

    return {"appointment": _appt_public(appt)}


async def _schedule_reminder(
    db: AsyncSession, appt: Appointment, recipient_email: str, phone: str
) -> None:
    """Hatırlatma satırını sms_reminders kuyruğuna ekler (reminder_worker tüketir).

    Bildirim artık e-posta ile gider; phone alanları kayıt/uyumluluk için
    saklanır (telefon yoksa boş şifrelenir).
    """
    from datetime import timedelta

    from app.models.sms_reminder import SmsReminder
    from app.security.phones import phone_hash

    appt_dt = datetime.combine(appt.date, appt.time, tzinfo=timezone.utc)
    send_at = appt_dt - timedelta(minutes=15)
    status = "pending" if send_at > datetime.now(timezone.utc) else "due"
    safe_phone = phone or ""
    db.add(
        SmsReminder(
            id=uuid.uuid4(),
            appointment_id=appt.id,
            phone_encrypted=encrypt_phone(safe_phone),
            phone_hash=phone_hash(safe_phone),
            phone_masked=mask_phone(safe_phone) if safe_phone else "—",
            recipient_email=recipient_email,
            message=(
                f"{appt.service_name} randevunuz 15 dakika sonra "
                f"({appt.time.strftime('%H:%M')}). İyi günler — Turuncu Randevu"
            ),
            send_at=send_at,
            status=status,
        )
    )


@router.get("/appointments")
async def list_appointments(
    db: AsyncSession = Depends(get_db),
    principal: Dict[str, Any] = Depends(get_current_principal),
):
    role = principal.get("role")
    if role == "customer":
        # Customer için RLS customer_self policy aktif olsun
        from sqlalchemy import text as _text

        await db.execute(
            _text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(principal["id"])},
        )
        stmt = select(Appointment).where(Appointment.customer_id == principal["id"])
    elif role == "staff":
        await set_rls_context(db, principal)
        stmt = select(Appointment).where(
            Appointment.business_id == principal["business_id"],
            Appointment.staff_id == principal["id"],
        )
    else:  # owner
        await set_rls_context(db, principal)
        stmt = select(Appointment).where(
            Appointment.business_id == principal["business_id"]
        )
    stmt = stmt.order_by(Appointment.date, Appointment.time).limit(500)
    rows = (await db.scalars(stmt)).all()
    return {"appointments": [_appt_public(a) for a in rows]}


@router.patch("/appointments/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: uuid.UUID,
    payload: CancelRequest,
    db: AsyncSession = Depends(get_db),
    principal: Dict[str, Any] = Depends(get_current_principal),
):
    # RLS bypass için principal'in business_id'sini set'le (customer ise self policy)
    if principal.get("business_id"):
        await set_rls_context(db, principal)
    else:
        from sqlalchemy import text as _text

        await db.execute(
            _text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(principal["id"])},
        )

    appt = await db.scalar(select(Appointment).where(Appointment.id == appointment_id))
    if not appt:
        raise HTTPException(status_code=404, detail="Randevu bulunamadı")

    allowed = appt.customer_id == principal["id"] or (
        principal.get("role") in ("owner", "staff")
        and principal.get("business_id") == appt.business_id
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="İptal yetkiniz yok")

    appt.status = "cancelled"
    appt.cancelled_at = datetime.now(timezone.utc)
    appt.cancelled_by = principal["id"]
    appt.cancel_reason = payload.reason

    db.add(
        AppointmentEvent(
            id=uuid.uuid4(),
            appointment_id=appt.id,
            event_type="cancelled",
            actor_id=principal["id"],
            actor_role=principal.get("role"),
            payload={"reason": payload.reason} if payload.reason else None,
        )
    )

    await db.flush()
    return {"appointment": _appt_public(appt)}


@router.delete("/appointments/{appointment_id}")
async def delete_appointment(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    principal: Dict[str, Any] = Depends(require_owner),
):
    """Sadece telefonla gelen manuel kayıtlar silinebilir (audit için cancel önerilir)."""
    await set_rls_context(db, principal)
    appt = await db.scalar(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.business_id == principal["business_id"],
        )
    )
    if not appt:
        raise HTTPException(status_code=404, detail="Randevu bulunamadı")
    if appt.source != "manual":
        raise HTTPException(
            status_code=400,
            detail="Sadece manuel oluşturulan randevular silinebilir; diğerleri iptal edilir",
        )
    await db.delete(appt)
    await db.flush()
    return {"deleted": True, "id": str(appointment_id)}


@router.post("/appointments/{appointment_id}/start")
async def start_appointment(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    principal: Dict[str, Any] = Depends(require_staff_or_owner),
):
    """Personel "İşlemi Başlat" — kiosk akışının ilk butonu."""
    await set_rls_context(db, principal)
    appt = await db.scalar(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.business_id == principal["business_id"],
        )
    )
    if not appt:
        raise HTTPException(status_code=404, detail="Randevu bulunamadı")

    # Personel sadece kendi randevusunu başlatabilir; patron herkesinkini
    if principal["role"] == "staff" and appt.staff_id != principal["id"]:
        raise HTTPException(
            status_code=403, detail="Bu randevu size atanmamış"
        )

    if appt.status not in ("booked",):
        raise HTTPException(
            status_code=409,
            detail=f"Randevu '{appt.status}' durumunda; başlatılamaz",
        )

    appt.status = "in_service"
    appt.started_at = datetime.now(timezone.utc)
    db.add(
        AppointmentEvent(
            id=uuid.uuid4(),
            appointment_id=appt.id,
            event_type="started",
            actor_id=principal["id"],
            actor_role=principal["role"],
        )
    )
    await db.flush()
    return {"appointment": _appt_public(appt)}


@router.post("/appointments/{appointment_id}/finish")
async def finish_appointment(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    principal: Dict[str, Any] = Depends(require_staff_or_owner),
):
    """Personel "İşlemi Bitir" — kiosk akışının ikinci butonu."""
    await set_rls_context(db, principal)
    appt = await db.scalar(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.business_id == principal["business_id"],
        )
    )
    if not appt:
        raise HTTPException(status_code=404, detail="Randevu bulunamadı")

    if principal["role"] == "staff" and appt.staff_id != principal["id"]:
        raise HTTPException(status_code=403, detail="Bu randevu size atanmamış")

    if appt.status not in ("in_service", "booked"):
        raise HTTPException(
            status_code=409,
            detail=f"Randevu '{appt.status}' durumunda; bitirilemez",
        )

    appt.status = "done"
    appt.finished_at = datetime.now(timezone.utc)
    if not appt.started_at:
        appt.started_at = appt.finished_at  # tek tıkla bitirilebilir
    db.add(
        AppointmentEvent(
            id=uuid.uuid4(),
            appointment_id=appt.id,
            event_type="finished",
            actor_id=principal["id"],
            actor_role=principal["role"],
        )
    )
    await db.flush()
    return {"appointment": _appt_public(appt)}


@router.get("/appointments/export")
async def export_appointments(
    db: AsyncSession = Depends(get_db),
    principal: Dict[str, Any] = Depends(require_staff_or_owner),
):
    await set_rls_context(db, principal)
    rows = (
        await db.scalars(
            select(Appointment)
            .where(Appointment.business_id == principal["business_id"])
            .order_by(Appointment.date, Appointment.time)
            .limit(1000)
        )
    ).all()
    return {"count": len(rows), "appointments": [_appt_public(a) for a in rows]}
