from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User


async def update_user_name(
    db: AsyncSession,
    *,
    user: User,
    name: str,
) -> User:
    user.name = name
    await db.flush()
    return user


async def deactivate_user(
    db: AsyncSession,
    *,
    user: User,
) -> User:
    user.is_active = False
    await db.flush()
    return user
