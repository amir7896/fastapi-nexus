"""add product reviews

Revision ID: k3f4a5b6c7d8
Revises: j2e3f4a5b6c7
Create Date: 2026-09-08 00:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "j2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "product_reviews" in inspector.get_table_names():
        return
    op.create_table(
        "product_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=True),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_product_reviews_user_product"),
    )
    op.create_index(op.f("ix_product_reviews_order_id"), "product_reviews", ["order_id"], unique=False)
    op.create_index(op.f("ix_product_reviews_product_id"), "product_reviews", ["product_id"], unique=False)
    op.create_index(op.f("ix_product_reviews_user_id"), "product_reviews", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "product_reviews" not in inspector.get_table_names():
        return
    op.drop_index(op.f("ix_product_reviews_user_id"), table_name="product_reviews")
    op.drop_index(op.f("ix_product_reviews_product_id"), table_name="product_reviews")
    op.drop_index(op.f("ix_product_reviews_order_id"), table_name="product_reviews")
    op.drop_table("product_reviews")
