"""assign support tickets, audit logs, and low-stock alerts

Revision ID: t2o3p4q5r6s7
Revises: s1n2o3p4q5r6
Create Date: 2026-09-08 18:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "t2o3p4q5r6s7"
down_revision: Union[str, Sequence[str], None] = "s1n2o3p4q5r6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "support_conversations" in tables:
        columns = {column["name"] for column in inspector.get_columns("support_conversations")}
        if "assigned_to_id" not in columns:
            op.add_column(
                "support_conversations",
                sa.Column("assigned_to_id", sa.Uuid(), nullable=True),
            )
            op.create_index(
                "ix_support_conversations_assigned_to_id",
                "support_conversations",
                ["assigned_to_id"],
            )
            op.create_foreign_key(
                "fk_support_conversations_assigned_to_id_users",
                "support_conversations",
                "users",
                ["assigned_to_id"],
                ["id"],
                ondelete="SET NULL",
                onupdate="CASCADE",
            )
        if "assigned_at" not in columns:
            op.add_column(
                "support_conversations",
                sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
            )

    if "products" in tables:
        columns = {column["name"] for column in inspector.get_columns("products")}
        if "low_stock_alerted_at" not in columns:
            op.add_column(
                "products",
                sa.Column("low_stock_alerted_at", sa.DateTime(timezone=True), nullable=True),
            )

    if "staff_audit_logs" not in tables:
        op.create_table(
            "staff_audit_logs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("actor_id", sa.Uuid(), nullable=True),
            sa.Column("actor_name", sa.String(length=80), nullable=False),
            sa.Column("actor_email", sa.String(length=255), nullable=False),
            sa.Column("action", sa.String(length=60), nullable=False),
            sa.Column("target_type", sa.String(length=40), nullable=False),
            sa.Column("target_id", sa.String(length=64), nullable=True),
            sa.Column("summary", sa.String(length=255), nullable=False),
            sa.Column("extra", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["actor_id"],
                ["users.id"],
                ondelete="SET NULL",
                onupdate="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_staff_audit_logs_actor_id", "staff_audit_logs", ["actor_id"])
        op.create_index("ix_staff_audit_logs_action", "staff_audit_logs", ["action"])
        op.create_index("ix_staff_audit_logs_created_at", "staff_audit_logs", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "staff_audit_logs" in tables:
        op.drop_index("ix_staff_audit_logs_created_at", table_name="staff_audit_logs")
        op.drop_index("ix_staff_audit_logs_action", table_name="staff_audit_logs")
        op.drop_index("ix_staff_audit_logs_actor_id", table_name="staff_audit_logs")
        op.drop_table("staff_audit_logs")

    if "products" in tables:
        columns = {column["name"] for column in inspector.get_columns("products")}
        if "low_stock_alerted_at" in columns:
            op.drop_column("products", "low_stock_alerted_at")

    if "support_conversations" in tables:
        columns = {column["name"] for column in inspector.get_columns("support_conversations")}
        if "assigned_at" in columns:
            op.drop_column("support_conversations", "assigned_at")
        if "assigned_to_id" in columns:
            op.drop_constraint(
                "fk_support_conversations_assigned_to_id_users",
                "support_conversations",
                type_="foreignkey",
            )
            op.drop_index("ix_support_conversations_assigned_to_id", table_name="support_conversations")
            op.drop_column("support_conversations", "assigned_to_id")
