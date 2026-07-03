from uuid import UUID

from pydantic import BaseModel, Field

from src.models import UserRole


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str
    organization_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    organization_id: UUID
    email: str
    name: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}
