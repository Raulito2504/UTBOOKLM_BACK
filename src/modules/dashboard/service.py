from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import DocumentStatus, StudyActivity, User
from src.modules.dashboard import repository
from src.modules.dashboard.schemas import (
    ActivityMetrics,
    ChatMetrics,
    DashboardMetricsResponse,
    DocumentMetrics,
    FlashcardMetrics,
    NotebookCardResponse,
    QuizMetrics,
)


async def record_activity(
    db: AsyncSession,
    *,
    current_user: User,
    activity_type: str,
    metadata_json: dict[str, Any] | None = None,
    activity_date: datetime | None = None,
) -> StudyActivity:
    return await repository.create_study_activity(
        db,
        user_id=current_user.id,
        activity_type=activity_type,
        activity_date=activity_date or datetime.now(timezone.utc),
        metadata_json=metadata_json,
    )


async def get_metrics(
    db: AsyncSession,
    *,
    current_user: User,
) -> DashboardMetricsResponse:
    document_counts = await repository.count_documents_by_status(
        db,
        organization_id=current_user.organization_id,
    )
    chat_total = await repository.count_chats(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
    )
    chat_messages = await repository.count_chat_messages(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
    )
    deck_count = await repository.count_flashcard_decks(db, user_id=current_user.id)
    card_count = await repository.count_flashcards(db, user_id=current_user.id)
    reviewed_count = await repository.count_reviewed_flashcards(
        db,
        user_id=current_user.id,
    )
    quiz_count = await repository.count_quizzes(db, user_id=current_user.id)
    attempt_count = await repository.count_quiz_attempts(db, user_id=current_user.id)
    average_score = await repository.average_quiz_score(db, user_id=current_user.id)
    activity_dates = await repository.list_activity_dates(db, user_id=current_user.id)

    return DashboardMetricsResponse(
        documents=DocumentMetrics(
            total=sum(document_counts.values()),
            ready=document_counts.get(DocumentStatus.READY, 0),
            processing=document_counts.get(DocumentStatus.PROCESSING, 0),
            failed=document_counts.get(DocumentStatus.FAILED, 0),
        ),
        chats=ChatMetrics(total=chat_total, messages=chat_messages),
        flashcards=FlashcardMetrics(
            decks=deck_count,
            cards=card_count,
            reviewed=reviewed_count,
        ),
        quizzes=QuizMetrics(
            total=quiz_count,
            attempts=attempt_count,
            average_score=round(average_score, 2) if average_score is not None else None,
        ),
        activity=_build_activity_metrics(activity_dates),
    )


async def list_activities(
    db: AsyncSession,
    *,
    current_user: User,
    limit: int = 20,
    offset: int = 0,
) -> list[StudyActivity]:
    return await repository.list_recent_activities(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


async def list_notebooks(
    db: AsyncSession,
    *,
    current_user: User,
    limit: int = 20,
    offset: int = 0,
) -> list[NotebookCardResponse]:
    chats = await repository.list_notebook_cards(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
    )
    return [
        NotebookCardResponse(
            id=chat.id,
            title=chat.title,
            source_count=len(chat.document_ids or []),
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )
        for chat in chats
    ]


def _build_activity_metrics(activity_dates: list[datetime]) -> ActivityMetrics:
    active_days = sorted({_as_date(activity_date) for activity_date in activity_dates})
    if not active_days:
        return ActivityMetrics(
            current_streak=0,
            longest_streak=0,
            total_active_days=0,
        )

    return ActivityMetrics(
        current_streak=_current_streak(active_days),
        longest_streak=_longest_streak(active_days),
        total_active_days=len(active_days),
    )


def _as_date(value: datetime) -> date:
    return value.date()


def _current_streak(active_days: list[date]) -> int:
    active_set = set(active_days)
    cursor = datetime.now(timezone.utc).date()
    if cursor not in active_set:
        cursor -= timedelta(days=1)
        if cursor not in active_set:
            return 0

    streak = 0
    while cursor in active_set:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _longest_streak(active_days: list[date]) -> int:
    longest = 1
    current = 1
    for previous, current_day in zip(active_days, active_days[1:], strict=False):
        if current_day == previous + timedelta(days=1):
            current += 1
        else:
            longest = max(longest, current)
            current = 1
    return max(longest, current)

