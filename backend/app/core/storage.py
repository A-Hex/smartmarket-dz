# backend/app/core/storage.py
"""
Local filesystem storage for uploaded datasets and generated reports.

Kept as a small, swappable module: a future S3/MinIO backend can implement
the same function signatures without touching callers.
"""
import os
import uuid
from typing import BinaryIO

from fastapi import UploadFile

from app.core.config import settings
from app.schemas.errors import ApiError

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
# Content-types commonly sent by browsers/clients for these extensions.
ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",  # some clients send this for CSV/XLSX; extension is the source of truth
}


def _extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def validate_upload(file: UploadFile) -> str:
    """
    Validate a dataset upload's extension and declared content-type.

    Returns the validated (lowercased) extension. Raises ApiError on mismatch,
    guarding against extension/content-type spoofing per the security requirements.
    """
    ext = _extension(file.filename or "")
    if ext not in ALLOWED_EXTENSIONS:
        raise ApiError(
            422,
            "unsupported_file_type",
            "Seuls les fichiers CSV et Excel (.csv, .xlsx, .xls) sont acceptés.",
        )
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ApiError(
            422,
            "content_type_mismatch",
            "Le type de contenu du fichier ne correspond pas à son extension.",
        )
    return ext


async def save_upload(file: UploadFile, company_id: uuid.UUID, ext: str) -> tuple[str, int]:
    """
    Stream an UploadFile to disk, enforcing MAX_UPLOAD_SIZE_MB.

    Returns (storage_path, size_bytes). Raises ApiError if the size limit is exceeded.
    """
    company_dir = os.path.join(settings.UPLOAD_DIR, str(company_id))
    os.makedirs(company_dir, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}{ext}"
    storage_path = os.path.join(company_dir, stored_name)

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    size = 0

    with open(storage_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                out.close()
                os.remove(storage_path)
                raise ApiError(
                    413,
                    "file_too_large",
                    f"Le fichier dépasse la taille maximale autorisée ({settings.MAX_UPLOAD_SIZE_MB} Mo).",
                )
            out.write(chunk)

    return storage_path, size


def delete_file(storage_path: str) -> None:
    """Best-effort delete of a stored file; ignores missing files."""
    try:
        os.remove(storage_path)
    except FileNotFoundError:
        pass
