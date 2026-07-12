import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    ChatMessage,
    ChatSession,
    Document,
    DocumentStatus,
    Exam,
    ExamAttempt,
    Flashcard,
    FlashcardDeck,
    StudyActivity,
    StudyProgress,
)


async def create_study_activity(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    activity_type: str,
    activity_date: datetime,
    metadata_json: dict[str, Any] | None = None,
) -> StudyActivity:
    activity = StudyActivity(
        user_id=user_id,
        activity_type=activity_type,
        activity_date=activity_date,
        metadata_json=metadata_json,
    )
    db.add(activity)
    await db.flush()
    return activity


async def count_documents_by_status(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
) -> dict[DocumentStatus, int]:
    result = await db.execute(
        select(Document.status, func.count(Document.id))
        .where(Document.organization_id == organization_id)
        .group_by(Document.status),
    )
    return {status: count for status, count in result.all()}


async def count_chats(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> int:
    return await _scalar_count(
        db,
        select(func.count(ChatSession.id)).where(
            ChatSession.user_id == user_id,
            ChatSession.organization_id == organization_id,
        ),
    )


async def count_chat_messages(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> int:
    return await _scalar_count(
        db,
        select(func.count(ChatMessage.id))
        .join(ChatSession, ChatMessage.chat_session_id == ChatSession.id)
        .where(
            ChatSession.user_id == user_id,
            ChatSession.organization_id == organization_id,
        ),
    )


async def count_flashcard_decks(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> int:
    return await _scalar_count(
        db,
        select(func.count(FlashcardDeck.id)).where(FlashcardDeck.user_id == user_id),
    )


async def count_flashcards(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> int:
    return await _scalar_count(
        db,
        select(func.count(Flashcard.id))
        .join(FlashcardDeck, Flashcard.deck_id == FlashcardDeck.id)
        .where(FlashcardDeck.user_id == user_id),
    )


async def count_reviewed_flashcards(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> int:
    return await _scalar_count(
        db,
        select(func.count(StudyProgress.id)).where(StudyProgress.user_id == user_id),
    )


async def count_quizzes(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> int:
    return await _scalar_count(
        db,
        select(func.count(Exam.id)).where(Exam.user_id == user_id),
    )


async def count_quiz_attempts(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> int:
    return await _scalar_count(
        db,
        select(func.count(ExamAttempt.id)).where(ExamAttempt.user_id == user_id),
    )


async def average_quiz_score(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> float | None:
    result = await db.execute(
        select(func.avg(ExamAttempt.score)).where(
            ExamAttempt.user_id == user_id,
            ExamAttempt.score.is_not(None),
        ),
    )
    value = result.scalar_one_or_none()
    return float(value) if value is not None else None


async def list_activity_dates(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[datetime]:
    result = await db.execute(
        select(StudyActivity.activity_date)
        .where(StudyActivity.user_id == user_id)
        .order_by(StudyActivity.activity_date),
    )
    return list(result.scalars().all())


async def list_recent_activities(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> list[StudyActivity]:
    result = await db.execute(
        select(StudyActivity)
        .where(StudyActivity.user_id == user_id)
        .order_by(StudyActivity.activity_date.desc(), StudyActivity.created_at.desc())
        .limit(limit)
        .offset(offset),
    )
    return list(result.scalars().all())


async def list_notebook_cards(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> list[ChatSession]:
    result = await db.execute(
        select(ChatSession)
        .where(
            ChatSession.user_id == user_id,
            ChatSession.organization_id == organization_id,
        )
        .order_by(ChatSession.updated_at.desc())
        .limit(limit)
        .offset(offset),
    )
    return list(result.scalars().all())


async def _scalar_count(db: AsyncSession, statement) -> int:
    result = await db.execute(statement)
    return int(result.scalar_one() or 0)

