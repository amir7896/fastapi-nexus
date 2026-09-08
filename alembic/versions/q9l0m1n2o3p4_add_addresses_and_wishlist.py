"""add saved addresses and wishlist tables

Revision ID: q9l0m1n2o3p4
Revises: p8k9l0m1n2o3
Create Date: 2026-09-08 17:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "q9l0m1n2o3p4"
down_revision: Union[str, Sequence[str], None] = "p8k9l0m1n2o3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "saved_addresses" not in tables:
        op.create_table(
            "saved_addresses",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("label", sa.String(length=40), nullable=True),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("phone", sa.String(length=30), nullable=False),
            sa.Column("address", sa.String(length=255), nullable=False),
            sa.Column("city", sa.String(length=80), nullable=False),
            sa.Column("country", sa.String(length=80), nullable=False),
            sa.Column("is_default", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                ondelete="CASCADE",
                onupdate="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_saved_addresses_user_id"), "saved_addresses", ["user_id"], unique=False)

    if "wishlist_items" not in tables:
        op.create_table(
            "wishlist_items",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("product_id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["product_id"],
                ["products.id"],
                ondelete="CASCADE",
                onupdate="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                ondelete="CASCADE",
                onupdate="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "product_id", name="uq_wishlist_items_user_product"),
        )
        op.create_index(op.f("ix_wishlist_items_user_id"), "wishlist_items", ["user_id"], unique=False)
        op.create_index(op.f("ix_wishlist_items_product_id"), "wishlist_items", ["product_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "wishlist_items" in tables:
        op.drop_index(op.f("ix_wishlist_items_product_id"), table_name="wishlist_items")
        op.drop_index(op.f("ix_wishlist_items_user_id"), table_name="wishlist_items")
        op.drop_table("wishlist_items")
    if "saved_addresses" in tables:
        op.drop_index(op.f("ix_saved_addresses_user_id"), table_name="saved_addresses")
        op.drop_table("saved_addresses")
