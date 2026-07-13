from src.core.database import Base
from src.models import UserRole
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


def test_user_role_values_match_product_roles() -> None:
    assert {role.value for role in UserRole} == {"admin", "teacher", "student"}


def test_study_practice_artifacts_track_notebook_and_documents() -> None:
    flashcard_columns = Base.metadata.tables["flashcard_decks"].columns
    exam_columns = Base.metadata.tables["exams"].columns

    assert "document_ids" in flashcard_columns
    assert "notebook_id" in flashcard_columns
    assert "document_ids" in exam_columns
    assert "notebook_id" in exam_columns
