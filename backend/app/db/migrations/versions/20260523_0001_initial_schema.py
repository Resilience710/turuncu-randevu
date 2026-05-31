"""initial schema — tüm tablolar

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-23

Bu migration Faz 1'in çıktısıdır:
- sectors, tenants, users, staff_users
- stations, services
- appointments (+unique partial slot index)
- appointment_events
- sessions, pending_customers
- sms_logs, sms_reminders

RLS politikaları Faz 2'de ayrı bir migration'da açılır.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Extensions ---
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # --- sectors ---
    op.create_table(
        "sectors",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(100), nullable=False),
        sa.Column("default_services", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- tenants ---
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sector_id", sa.String(50), sa.ForeignKey("sectors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("invite_code", sa.String(20), nullable=False, unique=True),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="beklemede"),
        sa.Column("verification_note", sa.Text, nullable=True),
        sa.Column("kvkk_text", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tenants_sector_id", "tenants", ["sector_id"])
    op.create_index("ix_tenants_location", "tenants", ["location"])
    op.create_index("ix_tenants_invite_code", "tenants", ["invite_code"])

    # --- users (müşteri) ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone_encrypted", sa.LargeBinary, nullable=False),
        sa.Column("phone_hash", sa.LargeBinary, nullable=False),
        sa.Column("phone_masked", sa.String(30), nullable=False),
        sa.Column("gmail", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("phone_verified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("kvkk_accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_phone_hash", "users", ["phone_hash"], unique=True)
    op.create_index("ix_users_gmail", "users", ["gmail"], unique=True)

    # --- staff_users ---
    op.create_table(
        "staff_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("phone_encrypted", sa.LargeBinary, nullable=True),
        sa.Column("phone_hash", sa.LargeBinary, nullable=True),
        sa.Column("phone_masked", sa.String(30), nullable=True),
        sa.Column("gmail", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("title", sa.String(100), nullable=True),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("station_label", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('owner','staff')", name="ck_staff_role"),
    )
    op.create_index("ix_staff_business_role", "staff_users", ["business_id", "role"])
    op.create_index("ix_staff_phone_hash", "staff_users", ["phone_hash"])
    op.create_index("ix_staff_gmail", "staff_users", ["gmail"])

    # --- stations ---
    op.create_table(
        "stations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_stations_business_position", "stations", ["business_id", "position"])

    # FK staff_users.station_id -> stations.id (modeller arası dairesel olmasın diye sonradan ekle)
    op.create_foreign_key(
        "fk_staff_station",
        "staff_users",
        "stations",
        ["station_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- services ---
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False, server_default="30"),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_services_business", "services", ["business_id"])

    # --- appointments ---
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("staff_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="SET NULL"), nullable=True),
        sa.Column("service_name", sa.String(200), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("time", sa.Time, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="booked"),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("customer_name", sa.String(200), nullable=True),
        sa.Column("customer_phone_encrypted", sa.LargeBinary, nullable=True),
        sa.Column("customer_phone_masked", sa.String(30), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="customer"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancel_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('booked','in_service','done','cancelled','no_show')",
            name="ck_appt_status",
        ),
        sa.CheckConstraint("source IN ('customer','manual')", name="ck_appt_source"),
    )
    op.create_index("ix_appt_business_date", "appointments", ["business_id", "date"])
    op.create_index("ix_appt_staff_status", "appointments", ["staff_id", "status"])
    op.create_index("ix_appt_customer", "appointments", ["customer_id"])
    # Slot çakışmasını DB seviyesinde garanti eden partial unique index
    op.execute(
        "CREATE UNIQUE INDEX uq_appt_active_slot ON appointments "
        "(business_id, staff_id, date, time) "
        "WHERE status IN ('booked','in_service')"
    )

    # --- appointment_events ---
    op.create_table(
        "appointment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role", sa.String(20), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('created','started','finished','cancelled','reminder_sent','no_show')",
            name="ck_appt_event_type",
        ),
    )
    op.create_index("ix_appt_event_appt_time", "appointment_events", ["appointment_id", "created_at"])

    # --- sessions ---
    op.create_table(
        "sessions",
        sa.Column("token", sa.String(128), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal_type", sa.String(20), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("principal_type IN ('customer','staff')", name="ck_session_principal"),
    )
    op.create_index("ix_sessions_user", "sessions", ["user_id"])
    op.create_index("ix_sessions_expires", "sessions", ["expires_at"])

    # --- pending_customers ---
    op.create_table(
        "pending_customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone_encrypted", sa.LargeBinary, nullable=False),
        sa.Column("phone_hash", sa.LargeBinary, nullable=False),
        sa.Column("phone_masked", sa.String(30), nullable=False),
        sa.Column("gmail", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("kvkk_accepted", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("otp_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_pending_phone_hash", "pending_customers", ["phone_hash"])
    op.create_index("ix_pending_gmail", "pending_customers", ["gmail"])
    op.create_index("ix_pending_expires", "pending_customers", ["expires_at"])

    # --- sms_logs ---
    op.create_table(
        "sms_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone_hash", sa.LargeBinary, nullable=False),
        sa.Column("phone_masked", sa.String(30), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("provider_response", sa.Text, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sms_logs_purpose_time", "sms_logs", ["purpose", "created_at"])

    # --- sms_reminders ---
    op.create_table(
        "sms_reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone_encrypted", sa.LargeBinary, nullable=False),
        sa.Column("phone_hash", sa.LargeBinary, nullable=False),
        sa.Column("phone_masked", sa.String(30), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("send_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sms_reminders_status_time", "sms_reminders", ["status", "send_at"])


def downgrade() -> None:
    op.drop_table("sms_reminders")
    op.drop_table("sms_logs")
    op.drop_table("pending_customers")
    op.drop_table("sessions")
    op.drop_table("appointment_events")
    op.drop_index("uq_appt_active_slot", table_name="appointments")
    op.drop_table("appointments")
    op.drop_table("services")
    op.drop_constraint("fk_staff_station", "staff_users", type_="foreignkey")
    op.drop_table("stations")
    op.drop_table("staff_users")
    op.drop_table("users")
    op.drop_table("tenants")
    op.drop_table("sectors")
