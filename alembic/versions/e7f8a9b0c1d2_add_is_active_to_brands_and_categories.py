"""add is_active to brands and categories

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-09-07 17:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(op.f("ix_categories_is_active"), "categories", ["is_active"], unique=False)

    op.add_column(
        "brands",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(op.f("ix_brands_is_active"), "brands", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_brands_is_active"), table_name="brands")
    op.drop_column("brands", "is_active")
    op.drop_index(op.f("ix_categories_is_active"), table_name="categories")
    op.drop_column("categories", "is_active")
