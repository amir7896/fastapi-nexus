"""add seen_at to support messages

Revision ID: m5h6i7j8k9l0
Revises: l4g5h6i7j8k9
Create Date: 2026-09-08 01:08:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m5h6i7j8k9l0"
down_revision: Union[str, Sequence[str], None] = "l4g5h6i7j8k9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "support_messages" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("support_messages")}
    if "seen_at" not in columns:
        op.add_column("support_messages", sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "support_messages" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("support_messages")}
    if "seen_at" in columns:
        op.drop_column("support_messages", "seen_at")
