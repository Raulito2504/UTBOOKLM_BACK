from uuid import UUID

from pydantic import BaseModel

from src.models import RoomRole, RoomVisibility


class RoomCreateRequest(BaseModel):
    name: str
    description: str | None = None
    visibility: RoomVisibility = RoomVisibility.PRIVATE


class RoomEvent(BaseModel):
    type: str
    payload: dict


class RoomMemberResponse(BaseModel):
    user_id: UUID
    role: RoomRole
