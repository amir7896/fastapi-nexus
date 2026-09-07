"""add brands and product/variant brand and category fks

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-09-07 17:20:00.000000

"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _inspector().has_table(name)


def _has_column(table: str, column: str) -> bool:
    return any(item["name"] == column for item in _inspector().get_columns(table))


def _has_index(table: str, name: str) -> bool:
    return any(item["name"] == name for item in _inspector().get_indexes(table))


def _has_fk(table: str, name: str) -> bool:
    return any(item["name"] == name for item in _inspector().get_foreign_keys(table))


def upgrade() -> None:
    if not _has_table("brands"):
        op.create_table(
            "brands",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("brands", "ix_brands_name"):
        op.create_index(op.f("ix_brands_name"), "brands", ["name"], unique=False)

    if not _has_column("products", "brand_id"):
        op.add_column("products", sa.Column("brand_id", sa.Uuid(), nullable=True))
    if not _has_index("products", "ix_products_brand_id"):
        op.create_index(op.f("ix_products_brand_id"), "products", ["brand_id"], unique=False)
    if not _has_fk("products", "fk_products_brand_id_brands"):
        op.create_foreign_key(
            "fk_products_brand_id_brands",
            "products",
            "brands",
            ["brand_id"],
            ["id"],
            ondelete="SET NULL",
            onupdate="CASCADE",
        )

    if not _has_column("product_variants", "brand_id"):
        op.add_column("product_variants", sa.Column("brand_id", sa.Uuid(), nullable=True))
    if not _has_column("product_variants", "category_id"):
        op.add_column("product_variants", sa.Column("category_id", sa.Uuid(), nullable=True))
    if not _has_index("product_variants", "ix_product_variants_brand_id"):
        op.create_index(op.f("ix_product_variants_brand_id"), "product_variants", ["brand_id"], unique=False)
    if not _has_index("product_variants", "ix_product_variants_category_id"):
        op.create_index(op.f("ix_product_variants_category_id"), "product_variants", ["category_id"], unique=False)
    if not _has_fk("product_variants", "fk_product_variants_brand_id_brands"):
        op.create_foreign_key(
            "fk_product_variants_brand_id_brands",
            "product_variants",
            "brands",
            ["brand_id"],
            ["id"],
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    if not _has_fk("product_variants", "fk_product_variants_category_id_categories"):
        op.create_foreign_key(
            "fk_product_variants_category_id_categories",
            "product_variants",
            "categories",
            ["category_id"],
            ["id"],
            ondelete="SET NULL",
            onupdate="CASCADE",
        )

    if _has_column("products", "brand"):
        conn = op.get_bind()
        rows = conn.execute(
            sa.text("SELECT DISTINCT brand FROM products WHERE brand IS NOT NULL AND TRIM(brand) <> ''")
        )
        for (name,) in rows:
            existing = conn.execute(
                sa.text("SELECT id FROM brands WHERE name = :name AND deleted_at IS NULL LIMIT 1"),
                {"name": name.strip()},
            ).first()
            if existing:
                brand_id = existing[0]
            else:
                brand_id = uuid4().hex
                conn.execute(
                    sa.text(
                        "INSERT INTO brands (id, name, created_at, updated_at) "
                        "VALUES (:id, :name, UTC_TIMESTAMP(), UTC_TIMESTAMP())"
                    ),
                    {"id": brand_id, "name": name.strip()},
                )
            conn.execute(
                sa.text("UPDATE products SET brand_id = :brand_id WHERE brand = :name"),
                {"brand_id": brand_id, "name": name},
            )
        conn.execute(
            sa.text(
                "UPDATE product_variants pv JOIN products p ON p.id = pv.product_id "
                "SET pv.brand_id = p.brand_id, pv.category_id = p.category_id"
            )
        )
        op.drop_column("products", "brand")


def downgrade() -> None:
    if not _has_column("products", "brand"):
        op.add_column("products", sa.Column("brand", sa.String(length=100), nullable=True))
    if _has_fk("product_variants", "fk_product_variants_category_id_categories"):
        op.drop_constraint("fk_product_variants_category_id_categories", "product_variants", type_="foreignkey")
    if _has_fk("product_variants", "fk_product_variants_brand_id_brands"):
        op.drop_constraint("fk_product_variants_brand_id_brands", "product_variants", type_="foreignkey")
    if _has_index("product_variants", "ix_product_variants_category_id"):
        op.drop_index(op.f("ix_product_variants_category_id"), table_name="product_variants")
    if _has_index("product_variants", "ix_product_variants_brand_id"):
        op.drop_index(op.f("ix_product_variants_brand_id"), table_name="product_variants")
    if _has_column("product_variants", "category_id"):
        op.drop_column("product_variants", "category_id")
    if _has_column("product_variants", "brand_id"):
        op.drop_column("product_variants", "brand_id")
    if _has_fk("products", "fk_products_brand_id_brands"):
        op.drop_constraint("fk_products_brand_id_brands", "products", type_="foreignkey")
    if _has_index("products", "ix_products_brand_id"):
        op.drop_index(op.f("ix_products_brand_id"), table_name="products")
    if _has_column("products", "brand_id"):
        op.drop_column("products", "brand_id")
    if _has_index("brands", "ix_brands_name"):
        op.drop_index(op.f("ix_brands_name"), table_name="brands")
    if _has_table("brands"):
        op.drop_table("brands")
