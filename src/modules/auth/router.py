from fastapi import APIRouter

from src.api.v1.dependencies import CurrentUser
from src.modules.auth.schemas import UserResponse


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"module": "auth", "status": "ready"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
