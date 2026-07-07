from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.modules.users import repository


async def update_profile(
    db: AsyncSession,
    *,
    user: User,
    name: str,
) -> User:
    return await repository.update_user_name(db, user=user, name=name)


async def deactivate_profile(
    db: AsyncSession,
    *,
    user: User,
) -> User:
    return await repository.deactivate_user(db, user=user)
