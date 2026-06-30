import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Organization, PlanType, User, UserRole


async def create_organization(
    db: AsyncSession,
    *,
    name: str,
    slug: str,
    plan: PlanType = PlanType.FREE,
) -> Organization:
    organization = Organization(name=name, slug=slug, plan=plan)
    db.add(organization)
    await db.flush()
    return organization


async def get_organization_by_slug(
    db: AsyncSession,
    *,
    slug: str,
) -> Organization | None:
    result = await db.execute(
        select(Organization).where(Organization.slug == slug),
    )
    return result.scalar_one_or_none()


async def get_user_by_id(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(
    db: AsyncSession,
    *,
    email: str,
) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    email: str,
    password_hash: str,
    name: str,
    role: UserRole = UserRole.MEMBER,
) -> User:
    user = User(
        organization_id=organization_id,
        email=email,
        password_hash=password_hash,
        name=name,
        role=role,
    )
    db.add(user)
    await db.flush()
    return user
