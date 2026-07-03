from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.models import NotificationStatus


class NotificationResponse(BaseModel):
    id: UUID
    title: str
    body: str
    status: NotificationStatus
    created_at: datetime
    read_at: datetime | None = None

    model_config = {"from_attributes": True}
