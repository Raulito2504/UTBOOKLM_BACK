import asyncio
import uuid
from types import SimpleNamespace

import pytest

from src.core.config import Settings
from src.modules.auth import google_oauth


def google_settings(**overrides: object) -> Settings:
    values = {
        "GOOGLE_AUTH_ENABLED": True,
        "GOOGLE_CLIENT_ID": "google-client-id",
        "GOOGLE_CLIENT_SECRET": "google-client-secret",
        "GOOGLE_REDIRECT_URI": "http://localhost:8000/api/v1/auth/google/callback",
        "FRONTEND_AUTH_CALLBACK_URL": "http://localhost:3000/auth/callback",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_google_auth_ready_rejects_disabled_config() -> None:
    settings = google_settings(GOOGLE_AUTH_ENABLED=False)

    with pytest.raises(google_oauth.GoogleAuthDisabledError):
        google_oauth.ensure_google_auth_ready(settings)


def test_google_auth_ready_rejects_missing_credentials() -> None:
    settings = google_settings(GOOGLE_CLIENT_SECRET=None)

    with pytest.raises(google_oauth.GoogleAuthConfigMissingError):
        google_oauth.ensure_google_auth_ready(settings)


def test_frontend_redirect_uses_fragment_tokens() -> None:
    redirect_url = google_oauth.build_frontend_auth_redirect_url(
        google_settings(),
        access_token="access-token",
        refresh_token="refresh-token",
    )

    assert redirect_url == (
        "http://localhost:3000/auth/callback"
        "#access_token=access-token&refresh_token=refresh-token&token_type=bearer"
    )


def test_google_login_uses_existing_active_user(monkeypatch) -> None:
    user = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        email="student@example.com",
        is_active=True,
    )

    async def get_user_by_email(db: object, *, email: str) -> object:
        assert email == "student@example.com"
        return user

    async def create_refresh_token(db: object, *, user: object) -> str:
        return "refresh-token"

    monkeypatch.setattr(
        google_oauth.repository,
        "get_user_by_email",
        get_user_by_email,
    )
    monkeypatch.setattr(
        google_oauth,
        "create_user_refresh_token",
        create_refresh_token,
    )
    monkeypatch.setattr(
        google_oauth,
        "create_user_access_token",
        lambda user: "access-token",
    )

    result = asyncio.run(
        google_oauth.login_or_create_google_user(
            SimpleNamespace(),
            profile=google_oauth.GoogleProfile(
                email="student@example.com",
                name="Student Example",
                email_verified=True,
            ),
        ),
    )

    assert result.user is user
    assert result.access_token == "access-token"
    assert result.refresh_token == "refresh-token"


def test_google_login_creates_user_when_email_is_new(monkeypatch) -> None:
    created_organization = SimpleNamespace(id=uuid.uuid4())
    created_user = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=created_organization.id,
        email="new@example.com",
        is_active=True,
    )

    async def get_user_by_email(db: object, *, email: str) -> None:
        assert email == "new@example.com"
        return None

    async def create_organization(db: object, *, name: str, slug: str) -> object:
        assert name == "New Student"
        assert slug.startswith("new-student-")
        return created_organization

    async def create_user(
        db: object,
        *,
        organization_id: uuid.UUID,
        email: str,
        password_hash: str,
        name: str,
    ) -> object:
        assert organization_id == created_organization.id
        assert email == "new@example.com"
        assert password_hash
        assert name == "New Student"
        return created_user

    async def create_refresh_token(db: object, *, user: object) -> str:
        return "refresh-token"

    monkeypatch.setattr(
        google_oauth.repository,
        "get_user_by_email",
        get_user_by_email,
    )
    monkeypatch.setattr(
        google_oauth.repository,
        "create_organization",
        create_organization,
    )
    monkeypatch.setattr(google_oauth.repository, "create_user", create_user)
    monkeypatch.setattr(
        google_oauth,
        "create_user_refresh_token",
        create_refresh_token,
    )
    monkeypatch.setattr(
        google_oauth,
        "create_user_access_token",
        lambda user: "access-token",
    )

    result = asyncio.run(
        google_oauth.login_or_create_google_user(
            SimpleNamespace(),
            profile=google_oauth.GoogleProfile(
                email="new@example.com",
                name="New Student",
                email_verified=True,
            ),
        ),
    )

    assert result.user is created_user
    assert result.access_token == "access-token"
    assert result.refresh_token == "refresh-token"
