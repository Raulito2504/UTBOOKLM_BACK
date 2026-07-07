import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models import UserRole


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    organization_name: str = Field(min_length=1, max_length=255)

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Email must be valid")
        return email

    @field_validator("name", "organization_name")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Email must be valid")
        return email


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)

    model_config = ConfigDict(extra="forbid")


class PasswordForgotRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Email must be valid")
        return email


class PasswordForgotResponse(BaseModel):
    message: str
    reset_token: str | None = None


class PasswordResetRequest(BaseModel):
    reset_token: str = Field(min_length=32, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)

    model_config = ConfigDict(extra="forbid")


class MessageResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    id: UUID
    organization_id: UUID
    email: str
    name: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
