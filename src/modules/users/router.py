from fastapi import APIRouter, status

from src.api.v1.dependencies import CurrentUser, DatabaseSession
from src.modules.auth.schemas import UserResponse
from src.modules.users import service
from src.modules.users.schemas import UserReplaceRequest, UserUpdateRequest


router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: UserUpdateRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> UserResponse:
    user = await service.update_profile(db, user=current_user, name=payload.name)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.put("/me", response_model=UserResponse)
async def replace_me(
    payload: UserReplaceRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> UserResponse:
    user = await service.update_profile(db, user=current_user, name=payload.name)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(current_user: CurrentUser, db: DatabaseSession) -> None:
    await service.deactivate_profile(db, user=current_user)
    await db.commit()
