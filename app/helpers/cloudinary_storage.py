"""Upload and delete product images in Cloudinary under Nexus/products."""

from functools import lru_cache
from io import BytesIO
from pathlib import PurePosixPath
from uuid import uuid4

import cloudinary
import cloudinary.api
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.core.logging import get_logger
from app.helpers.image_types import PRODUCT_IMAGE_FOLDER, StoredImage

logger = get_logger(__name__)


def _configure() -> None:
    settings = get_settings()
    if not settings.cloudinary_enabled:
        raise BadRequestError(
            "Cloudinary is not configured. Set CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET."
        )
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME.strip(),
        api_key=settings.CLOUDINARY_API_KEY.strip(),
        api_secret=settings.CLOUDINARY_API_SECRET.strip(),
        secure=True,
    )


@lru_cache(maxsize=1)
def ensure_product_folder() -> None:
    """Create Nexus/products in Cloudinary if it is missing."""
    _configure()
    try:
        cloudinary.api.create_folder(PRODUCT_IMAGE_FOLDER)
    except CloudinaryError as exc:
        logger.info("Cloudinary folder %s already exists or skipped: %s", PRODUCT_IMAGE_FOLDER, exc)


def upload_image(*, data: bytes, filename: str, content_type: str) -> StoredImage:
    _configure()
    ensure_product_folder()

    suffix = PurePosixPath(filename).suffix.lower()
    public_id = f"{PRODUCT_IMAGE_FOLDER}/{uuid4().hex}"
    try:
        result = cloudinary.uploader.upload(
            BytesIO(data),
            public_id=public_id,
            folder=None,
            resource_type="image",
            overwrite=False,
            unique_filename=False,
            filename=filename or f"product{suffix}",
            format=suffix.lstrip(".") or None,
        )
    except CloudinaryError as exc:
        logger.exception("Cloudinary upload failed")
        raise BadRequestError("Could not upload the image to Cloudinary") from exc

    url = result.get("secure_url") or result.get("url")
    stored_id = result.get("public_id") or public_id
    if not url:
        raise BadRequestError("Cloudinary did not return an image URL")
    return StoredImage(url=url, public_id=stored_id, provider="cloudinary")


def delete_image(public_id: str) -> None:
    if not public_id.strip():
        return
    _configure()
    try:
        cloudinary.uploader.destroy(public_id, resource_type="image", invalidate=True)
    except CloudinaryError as exc:
        logger.exception("Cloudinary delete failed for %s", public_id)
        raise BadRequestError("Could not delete the image from Cloudinary") from exc
