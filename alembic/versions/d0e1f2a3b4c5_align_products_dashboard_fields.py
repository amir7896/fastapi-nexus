"""align products with dashboard ecommerce fields

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b5
Create Date: 2026-08-31 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    if not _has_column("products", "brand"):
        op.add_column("products", sa.Column("brand", sa.String(length=100), nullable=True))
    if not _has_column("products", "sku"):
        op.add_column("products", sa.Column("sku", sa.String(length=100), nullable=True))
    if not _has_column("products", "price_sale"):
        op.add_column(
            "products",
            sa.Column("price_sale", sa.Numeric(precision=12, scale=2), nullable=True),
        )
    if not _has_column("products", "colors"):
        op.add_column("products", sa.Column("colors", sa.JSON(), nullable=True))
        op.execute(sa.text("UPDATE products SET colors = JSON_ARRAY() WHERE colors IS NULL"))
        op.alter_column("products", "colors", existing_type=sa.JSON(), nullable=False)
    if not _has_column("products", "status"):
        op.add_column(
            "products",
            sa.Column("status", sa.String(length=20), nullable=False, server_default=""),
        )
        op.alter_column("products", "status", server_default=None)

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes("products")}
    if "ix_products_sku" not in indexes:
        op.create_index(op.f("ix_products_sku"), "products", ["sku"], unique=False)

    if not _has_column("product_variants", "price_sale"):
        op.add_column(
            "product_variants",
            sa.Column("price_sale", sa.Numeric(precision=12, scale=2), nullable=True),
        )


def downgrade() -> None:
    if _has_column("product_variants", "price_sale"):
        op.drop_column("product_variants", "price_sale")

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes("products")}
    if "ix_products_sku" in indexes:
        op.drop_index(op.f("ix_products_sku"), table_name="products")

    for column in ("status", "colors", "price_sale", "sku", "brand"):
        if _has_column("products", column):
            op.drop_column("products", column)
