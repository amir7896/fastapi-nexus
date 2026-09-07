from urllib.parse import quote

CARRIER_TRACKING_URLS = {
    "ups": "https://www.ups.com/track?tracknum={n}",
    "usps": "https://tools.usps.com/go/TrackConfirmAction?tLabels={n}",
    "fedex": "https://www.fedex.com/fedextrack/?trknbr={n}",
    "dhl": "https://www.dhl.com/en/express/tracking.html?AWB={n}",
    "tcs": "https://www.tcsexpress.com/track/{n}",
    "leopard": "https://www.leopardscourier.com/tracking/?cn={n}",
    "pakistan post": "https://ep.gov.pk/track.asp?tn={n}",
}

SHIPPING_CARRIERS = (
    "UPS",
    "USPS",
    "FedEx",
    "DHL",
    "TCS",
    "Leopard",
    "Pakistan Post",
    "Other",
)


def canonicalize_carrier(carrier: str | None) -> str | None:
    raw = (carrier or "").strip()
    if not raw:
        return None
    lookup = {name.lower(): name for name in SHIPPING_CARRIERS}
    canonical = lookup.get(raw.lower())
    if canonical is None:
        raise ValueError("Unknown shipping carrier")
    return canonical


def build_tracking_url(carrier: str | None, tracking_number: str | None) -> str | None:
    number = (tracking_number or "").strip()
    if not number:
        return None
    key = (carrier or "").strip().lower()
    template = CARRIER_TRACKING_URLS.get(key)
    if not template:
        return None
    return template.format(n=quote(number))
