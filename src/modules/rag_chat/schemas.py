from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.models import MessageRole


class ChatCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    document_ids: list[UUID] = Field(default_factory=list)


class ChatUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    document_ids: list[UUID] | None = None


class ChatResponse(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    title: str
    document_ids: list[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RagSourceResponse(BaseModel):
    document_id: UUID
    chunk_id: UUID
    page_number: int | None = None
    score: float | None = None
    preview: str


class ChatMessageCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    id: UUID
    chat_session_id: UUID
    role: MessageRole
    content: str
    sources: dict[str, Any] | None = None
    tokens_used: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RagGenerateResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    sources: list[RagSourceResponse]


class DocumentIndexResponse(BaseModel):
    document_id: UUID
    indexed_chunks: int
    status: str
