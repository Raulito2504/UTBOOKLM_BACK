from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fastapi import UploadFile

from src.core.config import get_settings


class DocumentStorage(Protocol):
    backend: str

    def save(self, content: bytes, filename: str) -> str:
        pass

    def read(self, file_path: str) -> bytes:
        pass

    def delete(self, file_path: str) -> None:
        pass


class LocalDocumentStorage:
    backend = "local"

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


class S3DocumentStorage:
    def __init__(
        self,
        *,
        backend: str = "s3",
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        region_name: str | None = None,
    ) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("S3 storage requires boto3 to be installed") from exc

        settings = get_settings()
        self.backend = backend
        self.bucket = bucket or settings.s3_bucket or settings.minio_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
        )

    def save(self, content: bytes, filename: str) -> str:
        extension = Path(filename).suffix.lower()
        key = f"documents/{uuid4()}{extension}"
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content)
        return key

    def read(self, file_path: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=file_path)
        return response["Body"].read()

    def delete(self, file_path: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=file_path)


def validate_upload_file(file: UploadFile, size: int) -> None:
    settings = get_settings()
    extension = Path(file.filename or "").suffix.lower().lstrip(".")
    mime_type = (file.content_type or "").lower()
    if extension not in settings.allowed_document_extensions:
        raise ValueError("Unsupported file extension")
    if mime_type == "application/octet-stream":
        if extension not in {"md", "txt"}:
            raise ValueError("Unsupported file type")
    elif mime_type and mime_type not in settings.allowed_document_mime_types:
        raise ValueError("Unsupported file type")
    if size > settings.document_max_upload_bytes:
        raise ValueError("File is too large")


def get_document_storage() -> DocumentStorage:
    settings = get_settings()
    backend = settings.document_storage_backend.lower()
    if backend == "local":
        return LocalDocumentStorage()
    if backend == "s3":
        return S3DocumentStorage(
            backend=backend,
            endpoint_url=settings.s3_endpoint_url,
            access_key=settings.s3_access_key_id,
            secret_key=settings.s3_secret_access_key,
            bucket=settings.s3_bucket,
            region_name=settings.s3_region_name,
        )
    if backend == "minio":
        return S3DocumentStorage(
            backend=backend,
            endpoint_url=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket=settings.minio_bucket,
        )
    raise RuntimeError(f"Unsupported document storage backend: {backend}")
