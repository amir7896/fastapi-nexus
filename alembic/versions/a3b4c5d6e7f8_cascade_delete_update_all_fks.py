"""cascade delete and update on all foreign keys

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-09-04 12:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, old_constraint_name, columns, ref_table, ref_columns, new_name)
_FK_SPECS = [
    (
        "orders",
        "orders_ibfk_1",
        ["user_id"],
        "users",
        ["id"],
        "fk_orders_user_id_users",
    ),
    (
        "order_items",
        "order_items_ibfk_1",
        ["order_id"],
        "orders",
        ["id"],
        "fk_order_items_order_id_orders",
    ),
    (
        "order_items",
        "order_items_ibfk_2",
        ["product_id"],
        "products",
        ["id"],
        "fk_order_items_product_id_products",
    ),
    (
        "order_items",
        "fk_order_items_variant_id_product_variants",
        ["variant_id"],
        "product_variants",
        ["id"],
        "fk_order_items_variant_id_product_variants",
    ),
    (
        "cart_items",
        "cart_items_ibfk_1",
        ["product_id"],
        "products",
        ["id"],
        "fk_cart_items_product_id_products",
    ),
    (
        "cart_items",
        "cart_items_ibfk_2",
        ["user_id"],
        "users",
        ["id"],
        "fk_cart_items_user_id_users",
    ),
    (
        "cart_items",
        "fk_cart_items_variant_id_product_variants",
        ["variant_id"],
        "product_variants",
        ["id"],
        "fk_cart_items_variant_id_product_variants",
    ),
    (
        "products",
        "products_ibfk_1",
        ["category_id"],
        "categories",
        ["id"],
        "fk_products_category_id_categories",
    ),
    (
        "product_variants",
        "product_variants_ibfk_1",
        ["product_id"],
        "products",
        ["id"],
        "fk_product_variants_product_id_products",
    ),
    (
        "password_reset_tokens",
        "password_reset_tokens_ibfk_1",
        ["user_id"],
        "users",
        ["id"],
        "fk_password_reset_tokens_user_id_users",
    ),
    (
        "email_verification_tokens",
        "email_verification_tokens_ibfk_1",
        ["user_id"],
        "users",
        ["id"],
        "fk_email_verification_tokens_user_id_users",
    ),
]


def upgrade() -> None:
    for table, old_name, columns, ref_table, ref_cols, new_name in _FK_SPECS:
        op.drop_constraint(old_name, table, type_="foreignkey")
        op.create_foreign_key(
            new_name,
            table,
            ref_table,
            columns,
            ref_cols,
            ondelete="CASCADE",
            onupdate="CASCADE",
        )


def downgrade() -> None:
    for table, old_name, columns, ref_table, ref_cols, new_name in reversed(_FK_SPECS):
        op.drop_constraint(new_name, table, type_="foreignkey")
        # Restore prior behavior: mostly NO ACTION; variant order_items was SET NULL.
        ondelete = None
        if new_name == "fk_order_items_variant_id_product_variants":
            ondelete = "SET NULL"
        elif new_name in {
            "fk_cart_items_variant_id_product_variants",
            "fk_product_variants_product_id_products",
            "fk_password_reset_tokens_user_id_users",
            "fk_email_verification_tokens_user_id_users",
        }:
            ondelete = "CASCADE"
        op.create_foreign_key(
            old_name,
            table,
            ref_table,
            columns,
            ref_cols,
            ondelete=ondelete,
        )
