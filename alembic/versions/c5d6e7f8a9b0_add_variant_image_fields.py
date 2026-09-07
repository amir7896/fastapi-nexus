"""add variant image fields

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-09-07 16:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    if not _has_column("product_variants", "image_url"):
        op.add_column(
            "product_variants",
            sa.Column("image_url", sa.String(length=500), nullable=True),
        )
    if not _has_column("product_variants", "image_public_id"):
        op.add_column(
            "product_variants",
            sa.Column("image_public_id", sa.String(length=255), nullable=True),
        )


def downgrade() -> None:
    if _has_column("product_variants", "image_public_id"):
        op.drop_column("product_variants", "image_public_id")
    if _has_column("product_variants", "image_url"):
        op.drop_column("product_variants", "image_url")
