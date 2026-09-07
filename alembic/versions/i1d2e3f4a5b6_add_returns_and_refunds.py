"""add return request, refund, and delivered timestamps

Revision ID: i1d2e3f4a5b6
Revises: h0c1d2e3f4a5
Create Date: 2026-09-08 00:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "h0c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    op.execute(
        "ALTER TABLE orders MODIFY COLUMN status "
        "ENUM('PENDING','PAID','PROCESSING','SHIPPED','DELIVERED','CANCELLED','RETURNED') NOT NULL"
    )
    columns: list[tuple[str, sa.types.TypeEngine]] = [
        ("amount_refunded", sa.Numeric(12, 2)),
        ("stripe_refund_id", sa.String(length=255)),
        ("return_status", sa.String(length=20)),
        ("return_reason", sa.String(length=80)),
        ("return_details", sa.String(length=500)),
        ("return_admin_note", sa.String(length=500)),
        ("delivered_at", sa.DateTime(timezone=True)),
        ("refunded_at", sa.DateTime(timezone=True)),
    ]
    for name, col_type in columns:
        if _has_column("orders", name):
            continue
        if name == "amount_refunded":
            op.add_column(
                "orders",
                sa.Column(name, col_type, nullable=False, server_default="0.00"),
            )
        else:
            op.add_column("orders", sa.Column(name, col_type, nullable=True))


def downgrade() -> None:
    op.execute("UPDATE orders SET status = 'DELIVERED' WHERE status = 'RETURNED'")
    op.execute(
        "ALTER TABLE orders MODIFY COLUMN status "
        "ENUM('PENDING','PAID','PROCESSING','SHIPPED','DELIVERED','CANCELLED') NOT NULL"
    )
    for name in (
        "refunded_at",
        "delivered_at",
        "return_admin_note",
        "return_details",
        "return_reason",
        "return_status",
        "stripe_refund_id",
        "amount_refunded",
    ):
        if _has_column("orders", name):
            op.drop_column("orders", name)
