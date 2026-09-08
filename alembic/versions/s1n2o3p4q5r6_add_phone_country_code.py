"""add phone country code to addresses and order shipping

Revision ID: s1n2o3p4q5r6
Revises: r0m1n2o3p4q5
Create Date: 2026-09-08 18:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "s1n2o3p4q5r6"
down_revision: Union[str, Sequence[str], None] = "r0m1n2o3p4q5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "saved_addresses" in tables:
        columns = {column["name"] for column in inspector.get_columns("saved_addresses")}
        if "phone_country_code" not in columns:
            op.add_column(
                "saved_addresses",
                sa.Column("phone_country_code", sa.String(length=8), nullable=False, server_default=""),
            )
            op.alter_column("saved_addresses", "phone_country_code", server_default=None)

    if "orders" in tables:
        columns = {column["name"] for column in inspector.get_columns("orders")}
        if "shipping_phone_country_code" not in columns:
            op.add_column(
                "orders",
                sa.Column("shipping_phone_country_code", sa.String(length=8), nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "orders" in tables:
        columns = {column["name"] for column in inspector.get_columns("orders")}
        if "shipping_phone_country_code" in columns:
            op.drop_column("orders", "shipping_phone_country_code")
    if "saved_addresses" in tables:
        columns = {column["name"] for column in inspector.get_columns("saved_addresses")}
        if "phone_country_code" in columns:
            op.drop_column("saved_addresses", "phone_country_code")
