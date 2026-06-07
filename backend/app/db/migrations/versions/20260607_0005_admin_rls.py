"""Admin RLS bypass policy'leri — site yöneticisi tüm tenant'ları görür/yönetir

Revision ID: 0005_admin_rls
Revises: 0004_reminder_email
Create Date: 2026-06-07

FORCE RLS açık tablolarda, app.current_role='admin' GUC'u set'liyse tüm satırlara
izin veren permissive (OR'lanan) policy ekler. Normal kullanıcılar role'ü
owner/staff/customer set'lediği için bu policy onlara ekstra erişim vermez;
tenant izolasyonu aynen korunur.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0005_admin_rls"
down_revision: Union[str, None] = "0004_reminder_email"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ADMIN_TABLES = [
    "staff_users",
    "services",
    "stations",
    "appointments",
    "appointment_events",
    "sms_reminders",
]


def upgrade() -> None:
    for t in ADMIN_TABLES:
        op.execute(
            f"""
            CREATE POLICY p_{t}_admin ON {t}
              FOR ALL
              USING (current_setting('app.current_role', true) = 'admin')
              WITH CHECK (current_setting('app.current_role', true) = 'admin')
            """
        )


def downgrade() -> None:
    for t in ADMIN_TABLES:
        op.execute(f"DROP POLICY IF EXISTS p_{t}_admin ON {t}")
