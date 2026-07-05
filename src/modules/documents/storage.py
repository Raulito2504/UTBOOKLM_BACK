from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from src.core.config import get_settings


class LocalDocumentStorage:
    def __init__(self, base_dir: str | None = None) -> None:
        settings = get_settings()
        self.base_dir = Path(base_dir or settings.document_storage_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, content: bytes, filename: str) -> str:
        extension = Path(filename).suffix.lower()
        path = self.base_dir / f"{uuid4()}{extension}"
        path.write_bytes(content)
        return str(path)

    def read(self, file_path: str) -> bytes:
        return Path(file_path).read_bytes()

    def delete(self, file_path: str) -> None:
        path = Path(file_path)
        if path.exists():
            path.unlink()


def validate_upload_file(file: UploadFile, size: int) -> None:
    settings = get_settings()
    extension = Path(file.filename or "").suffix.lower().lstrip(".")
    mime_type = (file.content_type or "").lower()
    if extension not in settings.allowed_document_extensions:
        raise ValueError("Unsupported file extension")
    if mime_type and mime_type not in settings.allowed_document_mime_types:
        raise ValueError("Unsupported file type")
    if size > settings.document_max_upload_bytes:
        raise ValueError("File is too large")


def get_document_storage() -> LocalDocumentStorage:
    return LocalDocumentStorage()
