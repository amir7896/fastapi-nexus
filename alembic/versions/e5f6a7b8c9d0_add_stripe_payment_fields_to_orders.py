"""add stripe payment intent and payment method to orders

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-29 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("stripe_payment_intent_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("stripe_payment_method_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f("ix_orders_stripe_payment_intent_id"),
        "orders",
        ["stripe_payment_intent_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_orders_stripe_payment_intent_id"), table_name="orders")
    op.drop_column("orders", "stripe_payment_method_id")
    op.drop_column("orders", "stripe_payment_intent_id")
