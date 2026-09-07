"""add support conversations and messages

Revision ID: l4g5h6i7j8k9
Revises: k3f4a5b6c7d8
Create Date: 2026-09-08 00:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "l4g5h6i7j8k9"
down_revision: Union[str, Sequence[str], None] = "k3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "support_conversations" not in tables:
        op.create_table(
            "support_conversations",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("context_type", sa.String(length=20), nullable=False),
            sa.Column("order_id", sa.Uuid(), nullable=True),
            sa.Column("product_id", sa.Uuid(), nullable=True),
            sa.Column("subject", sa.String(length=160), nullable=False),
            sa.Column("last_message_preview", sa.String(length=200), nullable=True),
            sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_sender_id", sa.Uuid(), nullable=True),
            sa.Column("last_sender_is_staff", sa.Boolean(), nullable=False),
            sa.Column("customer_last_read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("staff_last_read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_support_conversations_user_id"), "support_conversations", ["user_id"], unique=False)
        op.create_index(op.f("ix_support_conversations_status"), "support_conversations", ["status"], unique=False)
        op.create_index(op.f("ix_support_conversations_context_type"), "support_conversations", ["context_type"], unique=False)
        op.create_index(op.f("ix_support_conversations_order_id"), "support_conversations", ["order_id"], unique=False)
        op.create_index(op.f("ix_support_conversations_product_id"), "support_conversations", ["product_id"], unique=False)
        op.create_index(op.f("ix_support_conversations_last_message_at"), "support_conversations", ["last_message_at"], unique=False)
    if "support_messages" not in tables:
        op.create_table(
            "support_messages",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("conversation_id", sa.Uuid(), nullable=False),
            sa.Column("sender_id", sa.Uuid(), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("is_staff", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_support_messages_conversation_id"), "support_messages", ["conversation_id"], unique=False)
        op.create_index(op.f("ix_support_messages_sender_id"), "support_messages", ["sender_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "support_messages" in tables:
        op.drop_index(op.f("ix_support_messages_sender_id"), table_name="support_messages")
        op.drop_index(op.f("ix_support_messages_conversation_id"), table_name="support_messages")
        op.drop_table("support_messages")
    if "support_conversations" in tables:
        op.drop_index(op.f("ix_support_conversations_last_message_at"), table_name="support_conversations")
        op.drop_index(op.f("ix_support_conversations_product_id"), table_name="support_conversations")
        op.drop_index(op.f("ix_support_conversations_order_id"), table_name="support_conversations")
        op.drop_index(op.f("ix_support_conversations_context_type"), table_name="support_conversations")
        op.drop_index(op.f("ix_support_conversations_status"), table_name="support_conversations")
        op.drop_index(op.f("ix_support_conversations_user_id"), table_name="support_conversations")
        op.drop_table("support_conversations")
