"""add stripe customer id to users

Revision ID: g9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-09-07 22:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g9b0c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    if not _has_column("users", "stripe_customer_id"):
        op.add_column(
            "users",
            sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        )
        op.create_index(
            op.f("ix_users_stripe_customer_id"),
            "users",
            ["stripe_customer_id"],
            unique=True,
        )


def downgrade() -> None:
    if _has_column("users", "stripe_customer_id"):
        op.drop_index(op.f("ix_users_stripe_customer_id"), table_name="users")
        op.drop_column("users", "stripe_customer_id")
