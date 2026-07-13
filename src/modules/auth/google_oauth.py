from dataclasses import dataclass
from urllib.parse import urlencode
import uuid

from authlib.integrations.httpx_client import AsyncOAuth2Client
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.security import generate_secure_token, hash_password
from src.models import User
from src.modules.auth import repository
from src.modules.auth.service import (
    create_user_access_token,
    create_user_refresh_token,
    organization_slug,
)


GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_SCOPE = "openid email profile"


class GoogleAuthDisabledError(Exception):
    pass


class GoogleAuthConfigMissingError(Exception):
    pass


class GoogleAuthCodeInvalidError(Exception):
    pass


class GoogleProfileInvalidError(Exception):
    pass


class GoogleEmailNotVerifiedError(Exception):
    pass


class GoogleUserInactiveError(Exception):
    pass


@dataclass(frozen=True)
class GoogleProfile:
    email: str
    name: str
    email_verified: bool


@dataclass(frozen=True)
class GoogleLoginResult:
    access_token: str
    refresh_token: str
    user: User


def ensure_google_auth_ready(settings: Settings) -> None:
    if not settings.google_auth_enabled:
        raise GoogleAuthDisabledError
    if not (
        settings.google_client_id
        and settings.google_client_secret
        and settings.google_redirect_uri
    ):
        raise GoogleAuthConfigMissingError


def create_google_authorization_url(settings: Settings) -> tuple[str, str]:
    ensure_google_auth_ready(settings)
    state = generate_secure_token()
    client = AsyncOAuth2Client(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
        scope=GOOGLE_SCOPE,
    )
    authorization_url, _ = client.create_authorization_url(
        GOOGLE_AUTHORIZE_URL,
        state=state,
        prompt="select_account",
    )
    return authorization_url, state


async def fetch_google_profile(settings: Settings, *, code: str) -> GoogleProfile:
    ensure_google_auth_ready(settings)
    client = AsyncOAuth2Client(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
        scope=GOOGLE_SCOPE,
    )
    try:
        await client.fetch_token(
            GOOGLE_TOKEN_URL,
            code=code,
            grant_type="authorization_code",
        )
        response = await client.get(GOOGLE_USERINFO_URL)
        response.raise_for_status()
    except Exception as exc:
        raise GoogleAuthCodeInvalidError from exc

    payload = response.json()
    email = payload.get("email")
    name = payload.get("name") or email
    email_verified = payload.get("email_verified")

    if not isinstance(email, str) or not email.strip():
        raise GoogleProfileInvalidError
    if not isinstance(name, str) or not name.strip():
        raise GoogleProfileInvalidError
    if email_verified is not True:
        raise GoogleEmailNotVerifiedError

    return GoogleProfile(
        email=email.strip().lower(),
        name=name.strip(),
        email_verified=email_verified,
    )


async def login_or_create_google_user(
    db: AsyncSession,
    *,
    profile: GoogleProfile,
) -> GoogleLoginResult:
    user = await repository.get_user_by_email(db, email=profile.email)
    if user is not None:
        if not user.is_active:
            raise GoogleUserInactiveError
        refresh_token = await create_user_refresh_token(db, user=user)
        return GoogleLoginResult(
            access_token=create_user_access_token(user),
            refresh_token=refresh_token,
            user=user,
        )

    organization = await repository.create_organization(
        db,
        name=profile.name,
        slug=f"{organization_slug(profile.name)}-{uuid.uuid4().hex[:8]}",
    )
    user = await repository.create_user(
        db,
        organization_id=organization.id,
        email=profile.email,
        password_hash=hash_password(generate_secure_token()),
        name=profile.name,
    )
    refresh_token = await create_user_refresh_token(db, user=user)
    return GoogleLoginResult(
        access_token=create_user_access_token(user),
        refresh_token=refresh_token,
        user=user,
    )


def build_frontend_auth_redirect_url(
    settings: Settings,
    *,
    access_token: str,
    refresh_token: str,
) -> str:
    fragment = urlencode(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        },
    )
    return f"{settings.frontend_auth_callback_url}#{fragment}"
