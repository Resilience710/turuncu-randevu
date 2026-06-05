"""sms_reminders.recipient_email — hatırlatmalar e-posta ile gider

Revision ID: 0004_reminder_email
Revises: 0003_staff_station_ids
Create Date: 2026-06-04

Bildirim kanalı SMS'ten e-postaya taşındı. Hatırlatma kuyruğundaki satırlara
alıcı e-posta adresi (nullable) eklenir. Eski satırlar e-postasız kalır ve
worker tarafından 'missing_email' olarak işaretlenir.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_reminder_email"
down_revision: Union[str, None] = "0003_staff_station_ids"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sms_reminders",
        sa.Column("recipient_email", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sms_reminders", "recipient_email")
