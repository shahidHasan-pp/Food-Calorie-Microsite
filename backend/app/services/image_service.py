import logging
import os
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_FILE_SIZE_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024


def _get_extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def validate_image(file: UploadFile, content_length: int | None) -> None:
    """
    Validate uploaded image format and size.
    Raises HTTPException on validation failure.
    """
    if file.filename is None:
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = _get_extension(file.filename)
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    if content_length and content_length > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB}MB.",
        )

    logger.debug("Image validated filename=%s ext=%s", file.filename, ext)


async def save_image(file: UploadFile) -> tuple[str, str, int]:
    """
    Read uploaded file bytes, validate actual size, and persist to disk.

    Returns:
        (file_path, file_type, file_size)
    """
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB}MB.",
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    ext = _get_extension(file.filename)
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest = upload_dir / unique_name
    dest.write_bytes(content)

    logger.info("Saved image file_path=%s size_bytes=%d", str(dest), file_size)
    return str(dest), ext, file_size
