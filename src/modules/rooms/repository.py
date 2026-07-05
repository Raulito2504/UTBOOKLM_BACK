import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import RoomMember, StudyRoom


async def get_room(
    db: AsyncSession,
    *,
    room_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> StudyRoom | None:
    result = await db.execute(
        select(StudyRoom).where(
            StudyRoom.id == room_id,
            StudyRoom.organization_id == organization_id,
        ),
    )
    return result.scalar_one_or_none()


async def list_room_members(
    db: AsyncSession,
    *,
    room_id: uuid.UUID,
) -> list[RoomMember]:
    result = await db.execute(
        select(RoomMember).where(RoomMember.room_id == room_id),
    )
    return list(result.scalars().all())
