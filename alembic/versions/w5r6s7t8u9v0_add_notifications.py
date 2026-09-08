"""add in-app notifications

Revision ID: w5r6s7t8u9v0
Revises: v4q5r6s7t8u9
Create Date: 2026-09-08 22:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "w5r6s7t8u9v0"
down_revision: Union[str, Sequence[str], None] = "v4q5r6s7t8u9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "notifications" in inspector.get_table_names():
        return
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=400), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_organization_id", "notifications", ["organization_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "notifications" not in inspector.get_table_names():
        return
    op.drop_index("ix_notifications_organization_id", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
