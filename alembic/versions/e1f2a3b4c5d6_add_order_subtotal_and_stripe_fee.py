"""add order subtotal and stripe fee

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-08-31 17:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("subtotal", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("stripe_fee", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.execute(sa.text("UPDATE orders SET subtotal = total, stripe_fee = 0 WHERE subtotal IS NULL"))
    op.alter_column("orders", "subtotal", existing_type=sa.Numeric(12, 2), nullable=False)
    op.alter_column(
        "orders",
        "stripe_fee",
        existing_type=sa.Numeric(12, 2),
        nullable=False,
        server_default="0",
    )
    op.alter_column("orders", "stripe_fee", server_default=None)


def downgrade() -> None:
    op.drop_column("orders", "stripe_fee")
    op.drop_column("orders", "subtotal")
