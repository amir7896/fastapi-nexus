"""add state to saved addresses and order shipping

Revision ID: r0m1n2o3p4q5
Revises: q9l0m1n2o3p4
Create Date: 2026-09-08 18:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "r0m1n2o3p4q5"
down_revision: Union[str, Sequence[str], None] = "q9l0m1n2o3p4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "saved_addresses" in tables:
        columns = {column["name"] for column in inspector.get_columns("saved_addresses")}
        if "state" not in columns:
            op.add_column(
                "saved_addresses",
                sa.Column("state", sa.String(length=80), nullable=False, server_default=""),
            )
            op.alter_column("saved_addresses", "state", server_default=None)

    if "orders" in tables:
        columns = {column["name"] for column in inspector.get_columns("orders")}
        if "shipping_state" not in columns:
            op.add_column(
                "orders",
                sa.Column("shipping_state", sa.String(length=80), nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "orders" in tables:
        columns = {column["name"] for column in inspector.get_columns("orders")}
        if "shipping_state" in columns:
            op.drop_column("orders", "shipping_state")
    if "saved_addresses" in tables:
        columns = {column["name"] for column in inspector.get_columns("saved_addresses")}
        if "state" in columns:
            op.drop_column("saved_addresses", "state")
