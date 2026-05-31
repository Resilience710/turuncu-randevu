"""staff_users.station_ids — çoklu istasyon ataması

Revision ID: 0003_staff_station_ids
Revises: 0002_rls_policies
Create Date: 2026-06-01

Bir personel birden fazla istasyona (koltuk/masa/oda) atanabilsin diye
staff_users tablosuna jsonb dizi kolonu ekler. station_id (tekil FK) primary
istasyon olarak kalır; station_ids tüm atanabilir istasyonları tutar.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_staff_station_ids"
down_revision: Union[str, None] = "0002_rls_policies"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "staff_users",
        sa.Column(
            "station_ids",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    # Mevcut tekil station_id'leri diziye taşı (varsa)
    op.execute(
        """
        UPDATE staff_users
        SET station_ids = jsonb_build_array(station_id::text)
        WHERE station_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("staff_users", "station_ids")
