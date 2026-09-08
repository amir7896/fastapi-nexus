"""add staff DM channel to support conversations

Revision ID: p8k9l0m1n2o3
Revises: o7j8k9l0m1n2
Create Date: 2026-09-08 17:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p8k9l0m1n2o3"
down_revision: Union[str, Sequence[str], None] = "o7j8k9l0m1n2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "support_conversations" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("support_conversations")}
    if "peer_id" not in columns:
        op.add_column(
            "support_conversations",
            sa.Column("peer_id", sa.Uuid(), nullable=True),
        )
        op.create_foreign_key(
            "fk_support_conversations_peer_id_users",
            "support_conversations",
            "users",
            ["peer_id"],
            ["id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
        )
        op.create_index("ix_support_conversations_peer_id", "support_conversations", ["peer_id"])
    if "channel" not in columns:
        op.add_column(
            "support_conversations",
            sa.Column("channel", sa.String(length=20), nullable=False, server_default="CUSTOMER"),
        )
        op.create_index("ix_support_conversations_channel", "support_conversations", ["channel"])
    indexes = {index["name"] for index in inspector.get_indexes("support_conversations")}
    if "uq_support_user_peer" not in indexes:
        op.create_index(
            "uq_support_user_peer",
            "support_conversations",
            ["user_id", "peer_id"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "support_conversations" not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in inspector.get_indexes("support_conversations")}
    if "uq_support_user_peer" in indexes:
        op.drop_index("uq_support_user_peer", table_name="support_conversations")
    columns = {column["name"] for column in inspector.get_columns("support_conversations")}
    if "channel" in columns:
        op.drop_index("ix_support_conversations_channel", table_name="support_conversations")
        op.drop_column("support_conversations", "channel")
    if "peer_id" in columns:
        op.drop_constraint("fk_support_conversations_peer_id_users", "support_conversations", type_="foreignkey")
        op.drop_index("ix_support_conversations_peer_id", table_name="support_conversations")
        op.drop_column("support_conversations", "peer_id")
