"""RLS politikaları — multi-tenant izolasyonun ikinci katmanı

Revision ID: 0002_rls_policies
Revises: 0001_initial_schema
Create Date: 2026-05-24

Tenant tablolarında Row Level Security'i açar.
FastAPI her tenant-scoped istekte transaction içinde şu GUC'ları set'ler:
    SET LOCAL app.current_business_id = '<uuid>';
    SET LOCAL app.current_user_id     = '<uuid>';
    SET LOCAL app.current_role        = 'owner|staff|customer';

GUC set edilmemişse current_setting('app.current_business_id', true) boş string
döner; politikalar bu durumda **hiçbir satırı eşleştirmez** — güvenli default.

NOT: Supabase'de FastAPI'nin bağlandığı rol RLS-enforced olmalı. Postgres
süperuser'ı (postgres role) RLS'i bypass eder; production'da custom bir DB
kullanıcısı (örn. `app_user`) oluşturulmalı ve DATABASE_URL ona bağlanmalı.

Public tablolar (RLS yok):
- sectors   : herkes okur
- tenants   : public browse için
- sessions  : Bearer token doğrulamasında tüm rolden okunur (token uniqueness
              güvenliği zaten yeterli)
- sms_logs  : sadece backend yazar/okur, dış erişim yok
- pending_customers : OTP akışı içinden ulaşılır
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002_rls_policies"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (tablo, business_id kolonu) — None ise customer self için ek policy yok
TENANT_TABLES = [
    "staff_users",
    "services",
    "stations",
    "appointments",
    "appointment_events",  # appointment üzerinden dolaylı; ayrı politika ile join
    "sms_reminders",
]


def upgrade() -> None:
    # 1) Tenant tablolarında RLS aç
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # 2) staff_users, services, stations — doğrudan business_id var
    for table in ("staff_users", "services", "stations"):
        op.execute(
            f"""
            CREATE POLICY p_{table}_tenant ON {table}
              FOR ALL
              USING (business_id::text = current_setting('app.current_business_id', true))
              WITH CHECK (business_id::text = current_setting('app.current_business_id', true))
            """
        )

    # sms_reminders'da business_id yok — appointments üzerinden filtrele
    op.execute(
        """
        CREATE POLICY p_sms_reminders_tenant ON sms_reminders
          FOR ALL
          USING (
            EXISTS (
              SELECT 1 FROM appointments a
              WHERE a.id = sms_reminders.appointment_id
                AND a.business_id::text = current_setting('app.current_business_id', true)
            )
          )
          WITH CHECK (
            EXISTS (
              SELECT 1 FROM appointments a
              WHERE a.id = sms_reminders.appointment_id
                AND a.business_id::text = current_setting('app.current_business_id', true)
            )
          )
        """
    )

    # 3) appointments — tenant + customer self
    op.execute(
        """
        CREATE POLICY p_appointments_tenant ON appointments
          FOR ALL
          USING (business_id::text = current_setting('app.current_business_id', true))
          WITH CHECK (business_id::text = current_setting('app.current_business_id', true))
        """
    )
    # Customer kendi randevularını farklı tenant'lara dağılmış olsa bile görür
    op.execute(
        """
        CREATE POLICY p_appointments_customer_self ON appointments
          FOR SELECT
          USING (customer_id::text = current_setting('app.current_user_id', true))
        """
    )

    # 4) appointment_events — appointments üzerinden join ile filtrele
    op.execute(
        """
        CREATE POLICY p_appt_events_tenant ON appointment_events
          FOR ALL
          USING (
            EXISTS (
              SELECT 1 FROM appointments a
              WHERE a.id = appointment_events.appointment_id
                AND a.business_id::text = current_setting('app.current_business_id', true)
            )
          )
          WITH CHECK (
            EXISTS (
              SELECT 1 FROM appointments a
              WHERE a.id = appointment_events.appointment_id
                AND a.business_id::text = current_setting('app.current_business_id', true)
            )
          )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS p_appt_events_tenant ON appointment_events")
    op.execute("DROP POLICY IF EXISTS p_appointments_customer_self ON appointments")
    op.execute("DROP POLICY IF EXISTS p_appointments_tenant ON appointments")
    for table in ("staff_users", "services", "stations", "sms_reminders"):
        op.execute(f"DROP POLICY IF EXISTS p_{table}_tenant ON {table}")

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
