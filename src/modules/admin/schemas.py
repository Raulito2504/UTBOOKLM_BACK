from pydantic import BaseModel, ConfigDict, model_validator

from src.models import UserRole
from src.modules.auth.schemas import UserResponse


class AdminUserUpdateRequest(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "AdminUserUpdateRequest":
        if self.role is None and self.is_active is None:
            raise ValueError("At least one field must be provided")
        return self


class UsersPagination(BaseModel):
    limit: int
    offset: int
    total: int


class UserListResponse(BaseModel):
    items: list[UserResponse]
    pagination: UsersPagination
