"""expand user_role enum for store staff

Revision ID: o7j8k9l0m1n2
Revises: n6i7j8k9l0m1
Create Date: 2026-09-08 16:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "o7j8k9l0m1n2"
down_revision: Union[str, Sequence[str], None] = "n6i7j8k9l0m1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    op.execute(
        "ALTER TABLE users MODIFY COLUMN role "
        "ENUM('USER', 'ADMIN', 'MANAGER', 'FINANCE', 'SUPPORT', 'FULFILLMENT') NOT NULL"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE users SET role = 'MANAGER' WHERE role IN ('FINANCE', 'SUPPORT', 'FULFILLMENT')"
    )
    op.execute("ALTER TABLE users MODIFY COLUMN role ENUM('USER', 'ADMIN', 'MANAGER') NOT NULL")
