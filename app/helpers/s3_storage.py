"""Upload and delete product images in Amazon S3 under Nexus/products."""

from functools import lru_cache
from mimetypes import guess_extension
from pathlib import PurePosixPath
from uuid import uuid4

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.core.logging import get_logger
from app.helpers.image_types import PRODUCT_IMAGE_FOLDER, StoredImage

logger = get_logger(__name__)


def _client():
    settings = get_settings()
    if not settings.s3_enabled:
        raise BadRequestError(
            "S3 is not configured. Set AWS_S3_BUCKET, AWS_ACCESS_KEY_ID, and AWS_SECRET_ACCESS_KEY."
        )
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID.strip(),
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY.strip(),
        region_name=settings.AWS_REGION.strip() or "us-east-1",
    )


@lru_cache(maxsize=1)
def ensure_product_folder() -> None:
    """Create the Nexus/products prefix so the folder exists in the bucket."""
    settings = get_settings()
    client = _client()
    try:
        client.put_object(
            Bucket=settings.AWS_S3_BUCKET.strip(),
            Key=f"{PRODUCT_IMAGE_FOLDER}/",
            Body=b"",
            ContentType="application/x-directory",
        )
    except (BotoCoreError, ClientError) as exc:
        logger.warning("Could not create S3 folder %s: %s", PRODUCT_IMAGE_FOLDER, exc)


def upload_image(*, data: bytes, filename: str, content_type: str) -> StoredImage:
    settings = get_settings()
    ensure_product_folder()

    suffix = PurePosixPath(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        suffix = guess_extension(content_type) or ".jpg"
        if suffix == ".jpe":
            suffix = ".jpg"

    key = f"{PRODUCT_IMAGE_FOLDER}/{uuid4().hex}{suffix}"
    try:
        _client().put_object(
            Bucket=settings.AWS_S3_BUCKET.strip(),
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("S3 upload failed")
        raise BadRequestError("Could not upload the image to S3") from exc

    return StoredImage(
        url=f"{settings.s3_public_base_url}/{key}",
        public_id=key,
        provider="s3",
    )


def delete_image(public_id: str) -> None:
    settings = get_settings()
    if not public_id.strip():
        return
    try:
        _client().delete_object(
            Bucket=settings.AWS_S3_BUCKET.strip(),
            Key=public_id,
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("S3 delete failed for %s", public_id)
        raise BadRequestError("Could not delete the image from S3") from exc
