from src.core.database import Base
import src.models  # noqa: F401


def test_models_register_expected_tables() -> None:
    expected_tables = {
        "api_keys",
        "chat_messages",
        "chat_sessions",
        "document_chunks",
        "documents",
        "flashcard_decks",
        "flashcards",
        "organizations",
        "study_progress",
        "users",
        "webhook_events",
    }

    assert expected_tables.issubset(Base.metadata.tables)
