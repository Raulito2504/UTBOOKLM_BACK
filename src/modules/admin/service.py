import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, UserRole
from src.modules.admin import repository


class UserNotFoundError(Exception):
    pass


class CannotModifySelfError(Exception):
    pass


async def list_organization_users(
    db: AsyncSession,
    *,
    admin_user: User,
    limit: int,
    offset: int,
) -> tuple[list[User], int]:
    users = await repository.list_users_by_organization(
        db,
        organization_id=admin_user.organization_id,
        limit=limit,
        offset=offset,
    )
    total = await repository.count_users_by_organization(
        db,
        organization_id=admin_user.organization_id,
    )
    return users, total


async def get_organization_user(
    db: AsyncSession,
    *,
    admin_user: User,
    user_id: uuid.UUID,
) -> User:
    user = await repository.get_user_by_organization(
        db,
        organization_id=admin_user.organization_id,
        user_id=user_id,
    )
    if user is None:
        raise UserNotFoundError
    return user


async def update_organization_user(
    db: AsyncSession,
    *,
    admin_user: User,
    user_id: uuid.UUID,
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> User:
    if user_id == admin_user.id and (role is not None or is_active is False):
        raise CannotModifySelfError

    user = await get_organization_user(db, admin_user=admin_user, user_id=user_id)
    return await repository.update_user_admin_fields(
        db,
        user=user,
        role=role,
        is_active=is_active,
    )
