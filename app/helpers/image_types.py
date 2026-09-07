from dataclasses import dataclass
from typing import Literal

StorageProvider = Literal["s3", "cloudinary"]

PRODUCT_IMAGE_FOLDER = "Nexus/products"
MAX_PRODUCT_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})


@dataclass(frozen=True, slots=True)
class StoredImage:
    url: str
    public_id: str
    provider: StorageProvider
