"""add product image fields

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-09-07 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, Sequence[str], None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    if not _has_column("products", "image_url"):
        op.add_column("products", sa.Column("image_url", sa.String(length=500), nullable=True))
    if not _has_column("products", "image_public_id"):
        op.add_column(
            "products",
            sa.Column("image_public_id", sa.String(length=255), nullable=True),
        )


def downgrade() -> None:
    if _has_column("products", "image_public_id"):
        op.drop_column("products", "image_public_id")
    if _has_column("products", "image_url"):
        op.drop_column("products", "image_url")
