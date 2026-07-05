import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, hash_password, verify_password
from src.models import User
from src.modules.auth import repository


def organization_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or uuid.uuid4().hex


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    name: str,
    organization_name: str,
) -> User:
    organization = await repository.create_organization(
        db,
        name=organization_name,
        slug=f"{organization_slug(organization_name)}-{uuid.uuid4().hex[:8]}",
    )
    user = await repository.create_user(
        db,
        organization_id=organization.id,
        email=email.lower(),
        password_hash=hash_password(password),
        name=name,
    )
    return user


async def authenticate_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> User | None:
    user = await repository.get_user_by_email(db, email=email.lower())
    if user is None or not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def create_user_access_token(user: User) -> str:
    return create_access_token(str(user.id), extra_claims={"org": str(user.organization_id)})
