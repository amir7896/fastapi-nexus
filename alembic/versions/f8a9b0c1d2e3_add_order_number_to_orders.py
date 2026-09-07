"""add unique order_number to orders

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-09-07 19:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FIRST_ORDER_NUMBER = 1001


def upgrade() -> None:
    op.add_column("orders", sa.Column("order_number", sa.Integer(), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id FROM orders ORDER BY created_at ASC, id ASC")).fetchall()
    for index, row in enumerate(rows, start=FIRST_ORDER_NUMBER):
        bind.execute(
            sa.text("UPDATE orders SET order_number = :n WHERE id = :id"),
            {"n": index, "id": row.id},
        )

    op.alter_column("orders", "order_number", existing_type=sa.Integer(), nullable=False)
    op.create_index(op.f("ix_orders_order_number"), "orders", ["order_number"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_orders_order_number"), table_name="orders")
    op.drop_column("orders", "order_number")
