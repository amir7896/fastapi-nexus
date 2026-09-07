"""add fulfillment statuses, shipping address, and tracking

Revision ID: h0c1d2e3f4a5
Revises: g9b0c1d2e3f4
Create Date: 2026-09-07 23:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h0c1d2e3f4a5"
down_revision: Union[str, Sequence[str], None] = "g9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    op.execute(
        "ALTER TABLE orders MODIFY COLUMN status "
        "ENUM('PENDING','PAID','PROCESSING','SHIPPED','DELIVERED','CANCELLED') NOT NULL"
    )
    columns = [
        ("shipping_name", sa.String(length=80)),
        ("shipping_phone", sa.String(length=30)),
        ("shipping_address", sa.String(length=255)),
        ("shipping_city", sa.String(length=80)),
        ("shipping_country", sa.String(length=80)),
        ("tracking_number", sa.String(length=100)),
    ]
    for name, col_type in columns:
        if not _has_column("orders", name):
            op.add_column("orders", sa.Column(name, col_type, nullable=True))


def downgrade() -> None:
    op.execute(
        "UPDATE orders SET status = 'PAID' "
        "WHERE status IN ('PROCESSING','SHIPPED','DELIVERED')"
    )
    op.execute(
        "ALTER TABLE orders MODIFY COLUMN status "
        "ENUM('PENDING','PAID','CANCELLED') NOT NULL"
    )
    for name in (
        "tracking_number",
        "shipping_country",
        "shipping_city",
        "shipping_address",
        "shipping_phone",
        "shipping_name",
    ):
        if _has_column("orders", name):
            op.drop_column("orders", name)
