import asyncio
from types import SimpleNamespace

from src.core.config import Settings, get_settings
from src.infrastructure.email.sender import EmailMessage, EmailSender
from src.modules.auth import service


def test_disabled_email_sender_accepts_valid_message() -> None:
    settings = Settings(
        _env_file=None,
        EMAIL_ENABLED=False,
        EMAIL_FROM="noreply@example.com",
    )
    sender = EmailSender(settings)

    sent = asyncio.run(
        sender.send(
            EmailMessage(
                to="student@example.com",
                subject="Reset password",
                body="Reset link",
            ),
        ),
    )

    assert sent is True


def test_disabled_email_sender_rejects_incomplete_message() -> None:
    settings = Settings(
        _env_file=None,
        EMAIL_ENABLED=False,
        EMAIL_FROM="noreply@example.com",
    )
    sender = EmailSender(settings)

    sent = asyncio.run(
        sender.send(
            EmailMessage(
                to="",
                subject="Reset password",
                body="Reset link",
            ),
        ),
    )

    assert sent is False


def test_build_password_reset_url_adds_token() -> None:
    reset_url = service.build_password_reset_url(
        "http://localhost:3000/reset-password?source=email",
        "reset-token",
    )

    assert reset_url == (
        "http://localhost:3000/reset-password?source=email&token=reset-token"
    )


def test_request_password_reset_sends_frontend_link(monkeypatch) -> None:
    captured_messages = []
    user = SimpleNamespace(
        id="user-id",
        email="student@example.com",
        name="Student Example",
        is_active=True,
    )

    async def get_user_by_email(db: object, *, email: str) -> object:
        assert email == "student@example.com"
        return user

    async def create_password_reset_token(
        db: object,
        *,
        user_id: str,
        token_hash: str,
        expires_at: object,
    ) -> object:
        assert user_id == "user-id"
        assert token_hash
        assert expires_at
        return SimpleNamespace()

    class CapturingEmailSender:
        async def send(self, message: EmailMessage) -> bool:
            captured_messages.append(message)
            return True

    monkeypatch.setattr(service.repository, "get_user_by_email", get_user_by_email)
    monkeypatch.setattr(
        service.repository,
        "create_password_reset_token",
        create_password_reset_token,
    )
    monkeypatch.setattr(service, "generate_secure_token", lambda: "plain-reset-token")
    monkeypatch.setattr(service, "get_email_sender", lambda: CapturingEmailSender())
    monkeypatch.setenv(
        "FRONTEND_PASSWORD_RESET_URL",
        "http://localhost:3000/reset-password",
    )
    get_settings.cache_clear()

    reset_token = asyncio.run(
        service.request_password_reset(
            SimpleNamespace(),
            email="Student@Example.com",
        ),
    )

    assert reset_token == "plain-reset-token"
    assert len(captured_messages) == 1
    assert captured_messages[0].to == "student@example.com"
    assert (
        "http://localhost:3000/reset-password?token=plain-reset-token"
        in captured_messages[0].body
    )

    get_settings.cache_clear()
