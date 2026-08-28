"""add stripe checkout session id to orders

Revision ID: c9d0e1f2a3b4
Revises: b7c8d9e0f1a2
Create Date: 2026-08-29 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("stripe_checkout_session_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f("ix_orders_stripe_checkout_session_id"),
        "orders",
        ["stripe_checkout_session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_orders_stripe_checkout_session_id"),
        table_name="orders",
    )
    op.drop_column("orders", "stripe_checkout_session_id")
