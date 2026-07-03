import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import WebSource


async def get_web_source(
    db: AsyncSession,
    *,
    source_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> WebSource | None:
    result = await db.execute(
        select(WebSource).where(
            WebSource.id == source_id,
            WebSource.organization_id == organization_id,
        ),
    )
    return result.scalar_one_or_none()


async def list_web_sources(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
) -> list[WebSource]:
    result = await db.execute(
        select(WebSource)
        .where(WebSource.organization_id == organization_id)
        .order_by(WebSource.created_at.desc()),
    )
    return list(result.scalars().all())
