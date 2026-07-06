import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, UserRole


async def count_users_by_organization(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(User)
        .where(User.organization_id == organization_id),
    )
    return int(result.scalar_one())


async def list_users_by_organization(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    limit: int,
    offset: int,
) -> list[User]:
    result = await db.execute(
        select(User)
        .where(User.organization_id == organization_id)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset),
    )
    return list(result.scalars().all())


async def get_user_by_organization(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
) -> User | None:
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
        ),
    )
    return result.scalar_one_or_none()


async def update_user_admin_fields(
    db: AsyncSession,
    *,
    user: User,
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> User:
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    await db.flush()
    return user
