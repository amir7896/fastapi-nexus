"""add organizations, memberships, invites, and tenant columns

Revision ID: u3p4q5r6s7t8
Revises: t2o3p4q5r6s7
Create Date: 2026-09-08 19:30:00.000000

"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "u3p4q5r6s7t8"
down_revision: Union[str, Sequence[str], None] = "t2o3p4q5r6s7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TENANT_TABLES = (
    "categories",
    "brands",
    "products",
    "orders",
    "cart_items",
    "wishlist_items",
    "support_conversations",
)


def _column_names(inspector, table: str) -> set[str]:
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _add_org_column(table: str, inspector) -> None:
    if table not in inspector.get_table_names():
        return
    columns = _column_names(inspector, table)
    if "organization_id" in columns:
        return
    op.add_column(table, sa.Column("organization_id", sa.Uuid(), nullable=True))
    op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "organizations" not in tables:
        op.create_table(
            "organizations",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("slug", sa.String(length=80), nullable=False),
            sa.Column("logo_url", sa.String(length=500), nullable=True),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="usd"),
            sa.Column("timezone", sa.String(length=60), nullable=False, server_default="UTC"),
            sa.Column("tax_rate", sa.Numeric(6, 3), nullable=False, server_default="0"),
            sa.Column("shipping_flat_rate", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("notify_orders", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("notify_low_stock", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("shop_url", sa.String(length=255), nullable=True),
            sa.Column("plan", sa.String(length=20), nullable=False, server_default="free"),
            sa.Column("plan_status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("stripe_billing_customer_id", sa.String(length=255), nullable=True),
            sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug"),
            sa.UniqueConstraint("stripe_billing_customer_id"),
        )
        op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)
        op.create_index(
            "ix_organizations_stripe_billing_customer_id",
            "organizations",
            ["stripe_billing_customer_id"],
            unique=True,
        )
        op.create_index(
            "ix_organizations_stripe_subscription_id",
            "organizations",
            ["stripe_subscription_id"],
        )

    if "organization_memberships" not in inspector.get_table_names():
        op.create_table(
            "organization_memberships",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("organization_id", sa.Uuid(), nullable=False),
            sa.Column("role", sa.Enum("USER", "ADMIN", "MANAGER", "FINANCE", "SUPPORT", "FULFILLMENT", name="user_role"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_org"),
        )
        op.create_index("ix_organization_memberships_user_id", "organization_memberships", ["user_id"])
        op.create_index(
            "ix_organization_memberships_organization_id",
            "organization_memberships",
            ["organization_id"],
        )

    if "organization_invites" not in inspector.get_table_names():
        op.create_table(
            "organization_invites",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("organization_id", sa.Uuid(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("role", sa.Enum("USER", "ADMIN", "MANAGER", "FINANCE", "SUPPORT", "FULFILLMENT", name="user_role"), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("invited_by_id", sa.Uuid(), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["invited_by_id"], ["users.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
        )
        op.create_index("ix_organization_invites_organization_id", "organization_invites", ["organization_id"])
        op.create_index("ix_organization_invites_email", "organization_invites", ["email"])
        op.create_index("ix_organization_invites_token_hash", "organization_invites", ["token_hash"], unique=True)

    inspector = sa.inspect(bind)
    users_columns = _column_names(inspector, "users")
    if "active_organization_id" not in users_columns:
        op.add_column("users", sa.Column("active_organization_id", sa.Uuid(), nullable=True))
        op.create_index("ix_users_active_organization_id", "users", ["active_organization_id"])
        op.create_foreign_key(
            "fk_users_active_organization_id_organizations",
            "users",
            "organizations",
            ["active_organization_id"],
            ["id"],
            ondelete="SET NULL",
            onupdate="CASCADE",
        )

    inspector = sa.inspect(bind)
    for table in _TENANT_TABLES:
        _add_org_column(table, inspector)
    audit_columns = _column_names(inspector, "staff_audit_logs")
    if "staff_audit_logs" in inspector.get_table_names() and "organization_id" not in audit_columns:
        op.add_column("staff_audit_logs", sa.Column("organization_id", sa.Uuid(), nullable=True))
        op.create_index("ix_staff_audit_logs_organization_id", "staff_audit_logs", ["organization_id"])

    org_id = uuid.uuid4().hex
    bind.execute(
        sa.text(
            "INSERT INTO organizations (id, name, slug, currency, timezone, tax_rate, "
            "shipping_flat_rate, notify_orders, notify_low_stock, plan, plan_status, "
            "created_at, updated_at) "
            "SELECT :id, 'Nexus', 'nexus', 'usd', 'UTC', 0, 0, 1, 1, 'free', 'active', "
            "UTC_TIMESTAMP(), UTC_TIMESTAMP() FROM DUAL "
            "WHERE NOT EXISTS (SELECT 1 FROM organizations WHERE slug = 'nexus')"
        ),
        {"id": org_id},
    )
    row = bind.execute(sa.text("SELECT id FROM organizations WHERE slug = 'nexus' LIMIT 1")).first()
    default_org_id = row[0] if row else org_id

    for table in _TENANT_TABLES:
        if table in inspector.get_table_names():
            bind.execute(
                sa.text(f"UPDATE {table} SET organization_id = :org_id WHERE organization_id IS NULL"),
                {"org_id": default_org_id},
            )
    if "staff_audit_logs" in inspector.get_table_names():
        bind.execute(
            sa.text(
                "UPDATE staff_audit_logs SET organization_id = :org_id WHERE organization_id IS NULL"
            ),
            {"org_id": default_org_id},
        )

    users = bind.execute(sa.text("SELECT id FROM users")).fetchall()
    for (user_id,) in users:
        bind.execute(
            sa.text(
                "INSERT INTO organization_memberships (id, user_id, organization_id, role, created_at) "
                "SELECT :mid, u.id, :org_id, u.role, UTC_TIMESTAMP() FROM users u "
                "WHERE u.id = :user_id AND NOT EXISTS ("
                "  SELECT 1 FROM organization_memberships m "
                "  WHERE m.user_id = u.id AND m.organization_id = :org_id"
                ")"
            ),
            {"mid": uuid.uuid4().hex, "org_id": default_org_id, "user_id": user_id},
        )
    bind.execute(
        sa.text(
            "UPDATE users SET active_organization_id = :org_id WHERE active_organization_id IS NULL"
        ),
        {"org_id": default_org_id},
    )

    for table in _TENANT_TABLES:
        if table not in inspector.get_table_names():
            continue
        try:
            op.alter_column(table, "organization_id", existing_type=sa.Uuid(), nullable=False)
        except Exception:
            pass
        try:
            op.create_foreign_key(
                f"fk_{table}_organization_id_organizations",
                table,
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="CASCADE",
                onupdate="CASCADE",
            )
        except Exception:
            pass

    if "staff_audit_logs" in inspector.get_table_names():
        try:
            op.create_foreign_key(
                "fk_staff_audit_logs_organization_id_organizations",
                "staff_audit_logs",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="CASCADE",
                onupdate="CASCADE",
            )
        except Exception:
            pass

    inspector = sa.inspect(bind)
    if "cart_items" in inspector.get_table_names():
        try:
            op.drop_constraint("uq_cart_items_user_product_variant", "cart_items", type_="unique")
        except Exception:
            pass
        try:
            op.create_unique_constraint(
                "uq_cart_items_org_user_product_variant",
                "cart_items",
                ["organization_id", "user_id", "product_id", "variant_id"],
            )
        except Exception:
            pass

    if "wishlist_items" in inspector.get_table_names():
        try:
            op.drop_constraint("uq_wishlist_items_user_product", "wishlist_items", type_="unique")
        except Exception:
            pass
        try:
            op.create_unique_constraint(
                "uq_wishlist_items_org_user_product",
                "wishlist_items",
                ["organization_id", "user_id", "product_id"],
            )
        except Exception:
            pass

    if "support_conversations" in inspector.get_table_names():
        try:
            op.drop_constraint("uq_support_user_peer", "support_conversations", type_="unique")
        except Exception:
            pass
        try:
            op.create_unique_constraint(
                "uq_support_org_user_peer",
                "support_conversations",
                ["organization_id", "user_id", "peer_id"],
            )
        except Exception:
            pass


def downgrade() -> None:
    pass
