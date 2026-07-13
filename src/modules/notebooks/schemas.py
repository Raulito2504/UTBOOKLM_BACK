from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.models import DocumentStatus


class NotebookSourcesUpdateRequest(BaseModel):
    document_ids: list[UUID] = Field(..., min_length=1)


class NotebookSourceResponse(BaseModel):
    id: UUID
    title: str
    original_filename: str | None = None
    mime_type: str | None = None
    file_size_bytes: int
    page_count: int
    status: DocumentStatus
    created_at: datetime

    model_config = {"from_attributes": True}
