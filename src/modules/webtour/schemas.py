from uuid import UUID

from pydantic import BaseModel

from src.models import JobStatus


class WebSourceRequest(BaseModel):
    url: str


class WebSourceResponse(BaseModel):
    id: UUID
    url: str
    title: str | None = None
    status: JobStatus
    last_error: str | None = None

    model_config = {"from_attributes": True}
