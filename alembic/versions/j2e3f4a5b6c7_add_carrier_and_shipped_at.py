"""add shipping carrier and shipped_at

Revision ID: j2e3f4a5b6c7
Revises: i1d2e3f4a5b6
Create Date: 2026-09-08 00:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "i1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    if not _has_column("orders", "shipping_carrier"):
        op.add_column("orders", sa.Column("shipping_carrier", sa.String(length=40), nullable=True))
    if not _has_column("orders", "shipped_at"):
        op.add_column("orders", sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for name in ("shipped_at", "shipping_carrier"):
        if _has_column("orders", name):
            op.drop_column("orders", name)
