from uuid import UUID

from pydantic import BaseModel, Field


class NotebookSourcesUpdateRequest(BaseModel):
    document_ids: list[UUID] = Field(..., min_length=1)

