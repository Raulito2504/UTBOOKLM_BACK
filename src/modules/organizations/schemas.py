from uuid import UUID

from pydantic import BaseModel

from src.models import PlanType, UserRole


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: PlanType

    model_config = {"from_attributes": True}


class OrganizationInviteRequest(BaseModel):
    email: str
    role: UserRole = UserRole.MEMBER
