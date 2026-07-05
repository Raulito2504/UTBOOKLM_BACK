import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Organization, OrganizationMembership


async def get_organization(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
) -> Organization | None:
    result = await db.execute(
        select(Organization).where(Organization.id == organization_id),
    )
    return result.scalar_one_or_none()


async def list_memberships(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
) -> list[OrganizationMembership]:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
        ),
    )
    return list(result.scalars().all())
