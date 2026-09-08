"""guest catalog support, team status, email prefs, coupons

Revision ID: x6s7t8u9v0w1
Revises: w5r6s7t8u9v0
Create Date: 2026-09-08 23:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "x6s7t8u9v0w1"
down_revision: Union[str, Sequence[str], None] = "w5r6s7t8u9v0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    membership_cols = {col["name"] for col in inspector.get_columns("organization_memberships")}
    if "is_active" not in membership_cols:
        op.add_column(
            "organization_memberships",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )

    user_cols = {col["name"] for col in inspector.get_columns("users")}
    if "notify_order_email" not in user_cols:
        op.add_column("users", sa.Column("notify_order_email", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "notify_support_email" not in user_cols:
        op.add_column("users", sa.Column("notify_support_email", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "notify_marketing_email" not in user_cols:
        op.add_column("users", sa.Column("notify_marketing_email", sa.Boolean(), nullable=False, server_default=sa.false()))

    order_cols = {col["name"] for col in inspector.get_columns("orders")}
    if "coupon_code" not in order_cols:
        op.add_column("orders", sa.Column("coupon_code", sa.String(length=40), nullable=True))
    if "discount_amount" not in order_cols:
        op.add_column(
            "orders",
            sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        )

    if "coupons" not in inspector.get_table_names():
        op.create_table(
            "coupons",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("organization_id", sa.Uuid(), nullable=False),
            sa.Column("code", sa.String(length=40), nullable=False),
            sa.Column("type", sa.String(length=16), nullable=False),
            sa.Column("value", sa.Numeric(12, 2), nullable=False),
            sa.Column("min_subtotal", sa.Numeric(12, 2), nullable=True),
            sa.Column("max_uses", sa.Integer(), nullable=True),
            sa.Column("used_count", sa.Integer(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "code", name="uq_coupons_org_code"),
        )
        op.create_index("ix_coupons_organization_id", "coupons", ["organization_id"])
        op.create_index("ix_coupons_code", "coupons", ["code"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "coupons" in inspector.get_table_names():
        op.drop_index("ix_coupons_code", table_name="coupons")
        op.drop_index("ix_coupons_organization_id", table_name="coupons")
        op.drop_table("coupons")
    order_cols = {col["name"] for col in inspector.get_columns("orders")}
    if "discount_amount" in order_cols:
        op.drop_column("orders", "discount_amount")
    if "coupon_code" in order_cols:
        op.drop_column("orders", "coupon_code")
    user_cols = {col["name"] for col in inspector.get_columns("users")}
    for name in ("notify_marketing_email", "notify_support_email", "notify_order_email"):
        if name in user_cols:
            op.drop_column("users", name)
    membership_cols = {col["name"] for col in inspector.get_columns("organization_memberships")}
    if "is_active" in membership_cols:
        op.drop_column("organization_memberships", "is_active")
