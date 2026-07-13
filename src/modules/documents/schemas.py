from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.models import DocumentStatus, JobStatus


class DocumentUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)

    model_config = {"str_strip_whitespace": True}


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    file_path: str
    original_filename: str | None = None
    mime_type: str | None = None
    storage_backend: str
    file_size_bytes: int
    page_count: int
    chunk_count: int | None = None
    status: DocumentStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    page_number: int | None = None
    vector_id: str | None = None
    tokens: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentChunkCreateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    page_number: int | None = Field(default=None, ge=1)
    chunk_index: int | None = Field(default=None, ge=0)
    tokens: int | None = Field(default=None, ge=0)

    model_config = {"str_strip_whitespace": True}


class IngestionJobResponse(BaseModel):
    id: UUID
    document_id: UUID
    status: JobStatus
    original_filename: str | None = None
    mime_type: str | None = None
    storage_backend: str
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
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
