import asyncio
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.core.config import get_settings
from src.core.events import EventPublisher
from src.core.exceptions import AppError, register_exception_handlers
from src.modules.documents.storage import LocalDocumentStorage, validate_upload_file
from src.modules.rag_chat.chunking import chunk_text


def test_app_imports_with_routers() -> None:
    module = importlib.import_module("src.main")

    paths = set(module.app.openapi()["paths"])

    assert "/api/v1/auth/health" in paths
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/refresh" in paths
    assert "/api/v1/auth/logout" in paths
    assert "/api/v1/auth/password/forgot" in paths
    assert "/api/v1/auth/password/reset" in paths
    assert "/api/v1/auth/google/login" in paths
    assert "/api/v1/auth/google/callback" in paths
    assert "/api/v1/users/me" in paths
    assert "patch" in module.app.openapi()["paths"]["/api/v1/users/me"]
    assert "put" in module.app.openapi()["paths"]["/api/v1/users/me"]
    assert "delete" in module.app.openapi()["paths"]["/api/v1/users/me"]
    assert "/api/v1/admin/users" in paths
    assert "/api/v1/admin/users/{user_id}" in paths
    assert "patch" in module.app.openapi()["paths"]["/api/v1/admin/users/{user_id}"]
    assert "/api/v1/dashboard/health" in paths
    assert "/api/v1/dashboard/metrics" in paths
    assert "/api/v1/dashboard/activity" in paths
    assert "/api/v1/dashboard/notebooks" in paths
    assert "/api/v1/docs/health" in paths
    assert "/api/v1/docs" in paths
    assert "post" in module.app.openapi()["paths"]["/api/v1/docs"]
    assert "get" in module.app.openapi()["paths"]["/api/v1/docs"]
    assert "/api/v1/docs/{document_id}" in paths
    assert "delete" in module.app.openapi()["paths"]["/api/v1/docs/{document_id}"]
    assert "/api/v1/docs/{document_id}/chunks" in paths
    assert "/api/v1/rag/health" in paths
    assert "/api/v1/rag/chats" in paths
    assert "post" in module.app.openapi()["paths"]["/api/v1/rag/chats"]
    assert "get" in module.app.openapi()["paths"]["/api/v1/rag/chats"]
    assert "/api/v1/rag/chats/{chat_id}" in paths
    assert "patch" in module.app.openapi()["paths"]["/api/v1/rag/chats/{chat_id}"]
    assert "delete" in module.app.openapi()["paths"]["/api/v1/rag/chats/{chat_id}"]
    assert "/api/v1/rag/chats/{chat_id}/messages" in paths
    assert "/api/v1/rag/documents/{document_id}/index" in paths
    assert "/api/v1/flashcards/health" in paths
    assert "/api/v1/flashcards/generate" in paths
    assert "/api/v1/flashcards/decks" in paths
    assert "/api/v1/flashcards/decks/{deck_id}" in paths
    assert "/api/v1/flashcards/decks/{deck_id}/cards" in paths
    assert "/api/v1/flashcards/{flashcard_id}/reviews" in paths
    assert "/api/v1/flashcards/quizzes/generate" in paths
    assert "/api/v1/flashcards/quizzes" in paths
    assert "/api/v1/flashcards/quizzes/{quiz_id}" in paths
    assert "/api/v1/flashcards/quizzes/{quiz_id}/questions" in paths
    assert "/api/v1/flashcards/quizzes/{quiz_id}/answers" in paths
    assert "/api/v1/flashcards/quizzes/{quiz_id}/results" in paths
    assert "/api/v1/flashcard-decks" in paths
    assert "/api/v1/flashcard-decks/{deck_id}" in paths
    assert "/api/v1/flashcard-decks/{deck_id}/cards" in paths
    assert "/api/v1/quizzes/generate" in paths
    assert "/api/v1/quizzes" in paths
    assert "/api/v1/quizzes/{quiz_id}" in paths
    assert "/api/v1/quizzes/{quiz_id}/questions" in paths
    assert "/api/v1/quizzes/{quiz_id}/answers" in paths
    assert "/api/v1/quizzes/{quiz_id}/results" in paths
    assert "/api/v1/rooms/health" in paths


def test_foundation_modules_import() -> None:
    modules = [
        "src.modules.auth.router",
        "src.modules.auth.service",
        "src.modules.auth.google_oauth",
        "src.modules.auth.schemas",
        "src.modules.admin.router",
        "src.modules.admin.repository",
        "src.modules.admin.service",
        "src.modules.admin.schemas",
        "src.modules.dashboard.router",
        "src.modules.dashboard.repository",
        "src.modules.dashboard.service",
        "src.modules.dashboard.schemas",
        "src.modules.users.router",
        "src.modules.users.service",
        "src.modules.users.schemas",
        "src.modules.documents.router",
        "src.modules.documents.service",
        "src.modules.documents.schemas",
        "src.modules.documents.tasks",
        "src.modules.flashcards.router",
        "src.modules.flashcards.service",
        "src.modules.flashcards.schemas",
        "src.modules.notifications.router",
        "src.modules.notifications.service",
        "src.modules.notifications.schemas",
        "src.modules.organizations.router",
        "src.modules.organizations.service",
        "src.modules.organizations.schemas",
        "src.modules.rag_chat.router",
        "src.modules.rag_chat.service",
        "src.modules.rag_chat.vector_store",
        "src.modules.rooms.router",
        "src.modules.rooms.service",
        "src.modules.rooms.schemas",
        "src.modules.streaks.router",
        "src.modules.streaks.service",
        "src.modules.streaks.schemas",
        "src.modules.webtour.router",
        "src.modules.webtour.service",
        "src.modules.webtour.schemas",
        "src.infrastructure.email.sender",
        "src.infrastructure.vectorstore.chroma_client",
    ]

    for module in modules:
        importlib.import_module(module)


def test_settings_defaults(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("GOOGLE_AUTH_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "google-client-secret")
    monkeypatch.setenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/v1/auth/google/callback",
    )
    monkeypatch.setenv(
        "FRONTEND_AUTH_CALLBACK_URL",
        "http://localhost:3000/auth/callback",
    )

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.app_env == "development"
    assert settings.auth_enabled is False
    assert settings.google_auth_enabled is True
    assert settings.google_client_id == "google-client-id"
    assert settings.google_client_secret == "google-client-secret"
    assert (
        settings.google_redirect_uri
        == "http://localhost:8000/api/v1/auth/google/callback"
    )
    assert settings.frontend_auth_callback_url == "http://localhost:3000/auth/callback"
    assert settings.effective_log_level == "INFO"
    assert settings.document_storage_backend == "local"
    assert "pdf" in settings.allowed_document_extensions
    assert settings.document_max_upload_bytes == 50 * 1024 * 1024
    assert settings.vector_store_provider == "chroma"
    assert settings.rag_top_k == 5
    assert settings.broker_url.startswith("redis://")


def test_local_storage_roundtrip(tmp_path) -> None:
    storage = LocalDocumentStorage(base_dir=str(tmp_path))
    path = storage.save(b"content", "notes.pdf")

    assert storage.read(path) == b"content"

    storage.delete(path)

    assert not Path(path).exists()


def test_upload_validation_accepts_pdf() -> None:
    file = SimpleNamespace(filename="notes.pdf", content_type="application/pdf")

    validate_upload_file(file, 1024)


def test_upload_validation_rejects_invalid_extension() -> None:
    file = SimpleNamespace(filename="notes.exe", content_type="application/pdf")

    with pytest.raises(ValueError):
        validate_upload_file(file, 1024)


def test_chunk_text_is_ordered() -> None:
    chunks = chunk_text("one two three four five", chunk_size=8, overlap=2)

    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    assert chunks[0].content.startswith("one")


def test_event_publisher_runs_handlers() -> None:
    events = []
    publisher = EventPublisher()

    async def handler(event_type: str, payload: dict) -> None:
        events.append((event_type, payload))

    publisher.subscribe(handler)
    asyncio.run(publisher.publish("study.completed", {"ok": True}))

    assert events == [("study.completed", {"ok": True})]


def test_app_error_response_uses_standard_shape() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="invalid_credentials",
            message="Invalid credentials",
        )

    response = TestClient(app).get("/boom", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 401
    assert response.json() == {
        "error_code": "invalid_credentials",
        "message": "Invalid credentials",
        "detail": None,
        "request_id": "test-request",
    }
