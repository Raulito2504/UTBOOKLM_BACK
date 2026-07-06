import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Organization, PasswordResetToken, PlanType, RefreshToken, User
from src.models import UserRole


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
    role: UserRole = UserRole.STUDENT,
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


async def create_refresh_token(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
) -> RefreshToken:
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(refresh_token)
    await db.flush()
    return refresh_token


async def get_refresh_token_by_hash(
    db: AsyncSession,
    *,
    token_hash: str,
) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash),
    )
    return result.scalar_one_or_none()


async def revoke_refresh_token(
    db: AsyncSession,
    *,
    refresh_token: RefreshToken,
    revoked_at: datetime,
) -> RefreshToken:
    refresh_token.revoked_at = revoked_at
    await db.flush()
    return refresh_token


async def create_password_reset_token(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
) -> PasswordResetToken:
    reset_token = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(reset_token)
    await db.flush()
    return reset_token


async def get_password_reset_token_by_hash(
    db: AsyncSession,
    *,
    token_hash: str,
) -> PasswordResetToken | None:
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash),
    )
    return result.scalar_one_or_none()


async def mark_password_reset_token_used(
    db: AsyncSession,
    *,
    reset_token: PasswordResetToken,
    used_at: datetime,
) -> PasswordResetToken:
    reset_token.used_at = used_at
    await db.flush()
    return reset_token


async def update_user_password_hash(
    db: AsyncSession,
    *,
    user: User,
    password_hash: str,
) -> User:
    user.password_hash = password_hash
    await db.flush()
    return user
