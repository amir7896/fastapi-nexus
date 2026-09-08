"""add organization logo public id

Revision ID: v4q5r6s7t8u9
Revises: u3p4q5r6s7t8
Create Date: 2026-09-08 20:04:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "v4q5r6s7t8u9"
down_revision: Union[str, Sequence[str], None] = "u3p4q5r6s7t8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    if not _has_column("organizations", "logo_public_id"):
        op.execute(
            sa.text(
                "ALTER TABLE organizations ADD COLUMN logo_public_id VARCHAR(255) NULL, "
                "ALGORITHM=INPLACE, LOCK=NONE"
            )
        )


def downgrade() -> None:
    if _has_column("organizations", "logo_public_id"):
        op.drop_column("organizations", "logo_public_id")
