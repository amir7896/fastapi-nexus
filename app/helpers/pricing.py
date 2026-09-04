"""Shared product pricing helpers."""

from decimal import Decimal

from app.helpers.stripe_fee import round_money
from app.models.product import Product
from app.models.product_variant import ProductVariant


def resolve_unit_price(
    product: Product,
    variant: ProductVariant | None = None,
) -> Decimal:
    """Return the chargeable unit price (sale price wins when lower than list)."""
    if variant is not None and variant.price is not None:
        list_price = Decimal(variant.price)
        sale_price = (
            Decimal(variant.price_sale) if variant.price_sale is not None else None
        )
    else:
        list_price = Decimal(product.price)
        if variant is not None and variant.price_sale is not None:
            sale_price = Decimal(variant.price_sale)
        elif product.price_sale is not None:
            sale_price = Decimal(product.price_sale)
        else:
            sale_price = None

    if sale_price is not None and sale_price < list_price:
        return round_money(sale_price)
    return round_money(list_price)
