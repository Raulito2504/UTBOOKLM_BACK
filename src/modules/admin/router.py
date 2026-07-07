from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, status

from src.api.v1.dependencies import AdminUser, DatabaseSession, pagination_params
from src.core.exceptions import AppError
from src.modules.admin import service
from src.modules.admin.schemas import AdminUserUpdateRequest, UserListResponse
from src.modules.admin.schemas import UsersPagination
from src.modules.auth.schemas import UserResponse


router = APIRouter()


@router.get("/users", response_model=UserListResponse)
async def list_users(
    current_user: AdminUser,
    db: DatabaseSession,
    pagination: Annotated[dict[str, int], Depends(pagination_params)],
) -> UserListResponse:
    users, total = await service.list_organization_users(
        db,
        admin_user=current_user,
        limit=pagination["limit"],
        offset=pagination["offset"],
    )
    return UserListResponse(
        items=[UserResponse.model_validate(user) for user in users],
        pagination=UsersPagination(
            limit=pagination["limit"],
            offset=pagination["offset"],
            total=total,
        ),
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: AdminUser,
    db: DatabaseSession,
) -> UserResponse:
    try:
        user = await service.get_organization_user(
            db,
            admin_user=current_user,
            user_id=user_id,
        )
    except service.UserNotFoundError:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="resource_not_found",
            message="User not found",
        ) from None
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdateRequest,
    current_user: AdminUser,
    db: DatabaseSession,
) -> UserResponse:
    try:
        user = await service.update_organization_user(
            db,
            admin_user=current_user,
            user_id=user_id,
            role=payload.role,
            is_active=payload.is_active,
        )
        await db.commit()
        await db.refresh(user)
    except service.CannotModifySelfError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            error_code="cannot_modify_self",
            message="You cannot change your own role or deactivate your own account",
        ) from None
    except service.UserNotFoundError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="resource_not_found",
            message="User not found",
        ) from None
    return UserResponse.model_validate(user)
