"""Dispatch product image uploads to S3 or Cloudinary from IMAGE_STORAGE_PROVIDER."""

from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.helpers import cloudinary_storage, s3_storage
from app.helpers.image_types import (
    ALLOWED_IMAGE_TYPES,
    MAX_PRODUCT_IMAGE_BYTES,
    PRODUCT_IMAGE_FOLDER,
    StoredImage,
)

_FORMAT_TO_TYPE = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
}


def validate_image_bytes(data: bytes) -> str:
    if not data:
        raise BadRequestError("Image file is empty")
    if len(data) > MAX_PRODUCT_IMAGE_BYTES:
        raise BadRequestError("Image must be 5MB or smaller")
    try:
        with Image.open(BytesIO(data)) as image:
            fmt = (image.format or "").upper()
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise BadRequestError("File is not a valid image") from exc
    content_type = _FORMAT_TO_TYPE.get(fmt)
    if content_type is None or content_type not in ALLOWED_IMAGE_TYPES:
        raise BadRequestError("Use a JPEG, PNG, WebP, or GIF image")
    return content_type


def upload_product_image(
    *,
    data: bytes,
    filename: str,
    content_type: str,
    folder: str = PRODUCT_IMAGE_FOLDER,
) -> StoredImage:
    provider = get_settings().image_storage_provider
    if provider == "s3":
        return s3_storage.upload_image(
            data=data,
            filename=filename,
            content_type=content_type,
            folder=folder,
        )
    if provider == "cloudinary":
        return cloudinary_storage.upload_image(
            data=data,
            filename=filename,
            content_type=content_type,
            folder=folder,
        )
    raise BadRequestError(
        "Image storage is not configured. Set IMAGE_STORAGE_PROVIDER to s3 or cloudinary."
    )


def delete_product_image(public_id: str) -> None:
    provider = get_settings().image_storage_provider
    if provider == "s3":
        s3_storage.delete_image(public_id)
        return
    if provider == "cloudinary":
        cloudinary_storage.delete_image(public_id)
        return
    raise BadRequestError(
        "Image storage is not configured. Set IMAGE_STORAGE_PROVIDER to s3 or cloudinary."
    )
