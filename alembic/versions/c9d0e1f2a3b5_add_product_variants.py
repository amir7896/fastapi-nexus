"""add product variants and wire cart/order lines

Revision ID: c9d0e1f2a3b5
Revises: b8c9d0e1f2a3
Create Date: 2026-08-31 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a3b5"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_variants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=True),
        sa.Column("color", sa.String(length=50), nullable=True),
        sa.Column("size", sa.String(length=50), nullable=True),
        sa.Column("material", sa.String(length=50), nullable=True),
        sa.Column("style", sa.String(length=50), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_product_variants_product_id"),
        "product_variants",
        ["product_id"],
        unique=False,
    )

    op.drop_constraint("uq_cart_items_user_product", "cart_items", type_="unique")
    op.add_column("cart_items", sa.Column("variant_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_cart_items_variant_id"), "cart_items", ["variant_id"], unique=False)
    op.create_foreign_key(
        "fk_cart_items_variant_id_product_variants",
        "cart_items",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.add_column("order_items", sa.Column("variant_id", sa.Uuid(), nullable=True))
    op.add_column("order_items", sa.Column("variant_name", sa.String(length=150), nullable=True))
    op.create_index(op.f("ix_order_items_variant_id"), "order_items", ["variant_id"], unique=False)
    op.create_foreign_key(
        "fk_order_items_variant_id_product_variants",
        "order_items",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_order_items_variant_id_product_variants", "order_items", type_="foreignkey")
    op.drop_index(op.f("ix_order_items_variant_id"), table_name="order_items")
    op.drop_column("order_items", "variant_name")
    op.drop_column("order_items", "variant_id")

    op.drop_constraint("fk_cart_items_variant_id_product_variants", "cart_items", type_="foreignkey")
    op.drop_index(op.f("ix_cart_items_variant_id"), table_name="cart_items")
    op.drop_column("cart_items", "variant_id")
    op.create_unique_constraint(
        "uq_cart_items_user_product",
        "cart_items",
        ["user_id", "product_id"],
    )

    op.drop_index(op.f("ix_product_variants_product_id"), table_name="product_variants")
    op.drop_table("product_variants")
