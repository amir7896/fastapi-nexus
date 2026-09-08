"""add MANAGER to user_role enum

Revision ID: n6i7j8k9l0m1
Revises: m5h6i7j8k9l0
Create Date: 2026-09-08 16:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "n6i7j8k9l0m1"
down_revision: Union[str, Sequence[str], None] = "m5h6i7j8k9l0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    op.execute("ALTER TABLE users MODIFY COLUMN role ENUM('USER', 'ADMIN', 'MANAGER') NOT NULL")


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'ADMIN' WHERE role = 'MANAGER'")
    op.execute("ALTER TABLE users MODIFY COLUMN role ENUM('USER', 'ADMIN') NOT NULL")
