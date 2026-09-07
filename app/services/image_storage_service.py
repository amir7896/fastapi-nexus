from fastapi import UploadFile

from app.core.exceptions import BadRequestError
from app.core.logging import get_logger
from app.helpers.image_storage import (
    delete_product_image,
    upload_product_image,
    validate_image_bytes,
)
from app.helpers.image_types import MAX_PRODUCT_IMAGE_BYTES, StoredImage

logger = get_logger(__name__)


class ImageStorageService:
    def upload(self, upload: UploadFile) -> StoredImage:
        data = upload.file.read(MAX_PRODUCT_IMAGE_BYTES + 1)
        if len(data) > MAX_PRODUCT_IMAGE_BYTES:
            raise BadRequestError("Image must be 5MB or smaller")
        content_type = validate_image_bytes(data)
        filename = upload.filename or "product"
        return upload_product_image(data=data, filename=filename, content_type=content_type)

    def delete(self, public_id: str | None, *, missing_ok: bool = False) -> None:
        if not public_id:
            return
        try:
            delete_product_image(public_id)
        except Exception:
            if missing_ok:
                logger.warning("Could not delete stored image %s", public_id, exc_info=True)
                return
            raise
