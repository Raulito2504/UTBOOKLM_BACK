from src.core.database import Base
import src.models  # noqa: F401


def test_models_register_expected_tables() -> None:
    expected_tables = {
        "api_keys",
        "chat_messages",
        "chat_sessions",
        "document_chunks",
        "documents",
        "exam_attempts",
        "exam_questions",
        "exams",
        "flashcard_decks",
        "flashcards",
        "ingestion_jobs",
        "notifications",
        "organization_invitations",
        "organization_memberships",
        "organizations",
        "password_reset_tokens",
        "rag_queries",
        "refresh_tokens",
        "room_members",
        "study_activities",
        "study_progress",
        "study_rooms",
        "users",
        "web_sources",
        "webhook_events",
    }

    assert expected_tables.issubset(Base.metadata.tables)
