import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime
from typing import Any

from src.models import StudyActivity, StudyProgress


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
