import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import StudyProgress


async def get_study_progress(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    flashcard_id: uuid.UUID,
) -> StudyProgress | None:
    result = await db.execute(
        select(StudyProgress).where(
            StudyProgress.user_id == user_id,
            StudyProgress.flashcard_id == flashcard_id,
        ),
    )
    return result.scalar_one_or_none()


async def create_study_progress(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    flashcard_id: uuid.UUID,
) -> StudyProgress:
    progress = StudyProgress(
        user_id=user_id,
        flashcard_id=flashcard_id,
    )
    db.add(progress)
    await db.flush()
    return progress
