from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        name = value.strip()
        if not name:
            raise ValueError("Name cannot be blank")
        return name

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "UserUpdateRequest":
        if self.name is None:
            raise ValueError("At least one field must be provided")
        return self


class UserReplaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Name cannot be blank")
        return name
