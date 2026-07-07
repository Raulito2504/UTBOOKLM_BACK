from datetime import UTC, datetime, timedelta
import logging
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.security import (
    create_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from src.infrastructure.email.sender import EmailMessage, get_email_sender
from src.models import PasswordResetToken, RefreshToken, User
from src.modules.auth import repository


logger = logging.getLogger(__name__)


class EmailAlreadyRegisteredError(Exception):
    pass


class RefreshTokenInvalidError(Exception):
    pass


class RefreshTokenExpiredError(Exception):
    pass


class RefreshTokenRevokedError(Exception):
    pass


class PasswordResetTokenInvalidError(Exception):
    pass


class PasswordResetTokenExpiredError(Exception):
    pass


class PasswordResetTokenUsedError(Exception):
    pass


def organization_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or uuid.uuid4().hex


def build_password_reset_url(base_url: str, token: str) -> str:
    parts = urlsplit(base_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["token"] = token
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        )
    )


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    name: str,
    organization_name: str,
) -> User:
    normalized_email = email.lower()
    existing_user = await repository.get_user_by_email(db, email=normalized_email)
    if existing_user is not None:
        raise EmailAlreadyRegisteredError

    organization = await repository.create_organization(
        db,
        name=organization_name,
        slug=f"{organization_slug(organization_name)}-{uuid.uuid4().hex[:8]}",
    )
    user = await repository.create_user(
        db,
        organization_id=organization.id,
        email=normalized_email,
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
    return create_access_token(
        str(user.id),
        extra_claims={"org": str(user.organization_id)},
    )


async def create_user_refresh_token(db: AsyncSession, *, user: User) -> str:
    settings = get_settings()
    token = generate_secure_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    await repository.create_refresh_token(
        db,
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=expires_at,
    )
    return token


async def validate_refresh_token(
    db: AsyncSession,
    *,
    refresh_token: str,
) -> tuple[RefreshToken, User]:
    token_record = await repository.get_refresh_token_by_hash(
        db,
        token_hash=hash_token(refresh_token),
    )
    if token_record is None:
        raise RefreshTokenInvalidError
    if token_record.revoked_at is not None:
        raise RefreshTokenRevokedError

    now = datetime.now(UTC)
    if token_record.expires_at.tzinfo is None:
        now = now.replace(tzinfo=None)
    if token_record.expires_at <= now:
        raise RefreshTokenExpiredError

    user = await repository.get_user_by_id(db, user_id=token_record.user_id)
    if user is None or not user.is_active:
        raise RefreshTokenInvalidError
    return token_record, user


async def refresh_access_token(db: AsyncSession, *, refresh_token: str) -> str:
    _, user = await validate_refresh_token(db, refresh_token=refresh_token)
    return create_user_access_token(user)


async def revoke_user_refresh_token(
    db: AsyncSession,
    *,
    refresh_token: str,
) -> None:
    token_record, _ = await validate_refresh_token(db, refresh_token=refresh_token)
    await repository.revoke_refresh_token(
        db,
        refresh_token=token_record,
        revoked_at=datetime.now(UTC),
    )


async def request_password_reset(
    db: AsyncSession,
    *,
    email: str,
) -> str | None:
    user = await repository.get_user_by_email(db, email=email.lower())
    if user is None or not user.is_active:
        return None

    settings = get_settings()
    token = generate_secure_token()
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.password_reset_token_expire_minutes,
    )
    await repository.create_password_reset_token(
        db,
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=expires_at,
    )

    sender = get_email_sender()
    reset_url = build_password_reset_url(settings.frontend_password_reset_url, token)
    email_sent = await sender.send(
        EmailMessage(
            to=user.email,
            subject="Reset your UTBookLM password",
            body=(
                "Use this link to reset your UTBookLM password:\n\n"
                f"{reset_url}\n\n"
                "This link expires in "
                f"{settings.password_reset_token_expire_minutes} minutes."
            ),
            to_name=user.name,
        ),
    )
    if not email_sent:
        logger.warning("Password reset email was not delivered")
    return token


async def validate_password_reset_token(
    db: AsyncSession,
    *,
    reset_token: str,
) -> tuple[PasswordResetToken, User]:
    token_record = await repository.get_password_reset_token_by_hash(
        db,
        token_hash=hash_token(reset_token),
    )
    if token_record is None:
        raise PasswordResetTokenInvalidError
    if token_record.used_at is not None:
        raise PasswordResetTokenUsedError

    now = datetime.now(UTC)
    if token_record.expires_at.tzinfo is None:
        now = now.replace(tzinfo=None)
    if token_record.expires_at <= now:
        raise PasswordResetTokenExpiredError

    user = await repository.get_user_by_id(db, user_id=token_record.user_id)
    if user is None or not user.is_active:
        raise PasswordResetTokenInvalidError
    return token_record, user


async def reset_password(
    db: AsyncSession,
    *,
    reset_token: str,
    new_password: str,
) -> None:
    token_record, user = await validate_password_reset_token(
        db,
        reset_token=reset_token,
    )
    await repository.update_user_password_hash(
        db,
        user=user,
        password_hash=hash_password(new_password),
    )
    await repository.mark_password_reset_token_used(
        db,
        reset_token=token_record,
        used_at=datetime.now(UTC),
    )
