"""add stock to products

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-08-31 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing products get a usable default so current catalog isn't zeroed out.
    op.add_column(
        "products",
        sa.Column("stock", sa.Integer(), nullable=False, server_default="100"),
    )
    op.alter_column("products", "stock", server_default=None)


def downgrade() -> None:
    op.drop_column("products", "stock")
