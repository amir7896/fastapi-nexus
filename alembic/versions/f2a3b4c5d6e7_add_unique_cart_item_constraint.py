"""add unique cart item constraint

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-09-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # MySQL allows multiple NULLs in a UNIQUE column, so variant-less rows
    # can still coexist only one-per-(user, product, NULL) is not guaranteed;
    # the app merge path remains the primary guard for those rows.
    op.create_unique_constraint(
        "uq_cart_items_user_product_variant",
        "cart_items",
        ["user_id", "product_id", "variant_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_cart_items_user_product_variant",
        "cart_items",
        type_="unique",
    )
