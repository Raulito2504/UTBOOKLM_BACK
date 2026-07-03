from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.models import DocumentStatus, JobStatus


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    file_path: str
    original_filename: str | None = None
    mime_type: str | None = None
    storage_backend: str
    file_size_bytes: int
    page_count: int
    status: DocumentStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class IngestionJobResponse(BaseModel):
    id: UUID
    document_id: UUID
    status: JobStatus
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    ingestion_job: IngestionJobResponse


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class DocumentDetailResponse(BaseModel):
    document: DocumentResponse
    chunk_count: int
    ingestion_job: IngestionJobResponse | None = None


class DocumentStatusResponse(BaseModel):
    document_id: UUID
    status: DocumentStatus
    ingestion_job: IngestionJobResponse | None = None
