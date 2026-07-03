from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Organization
from src.modules.organizations import repository
import uuid


async def get_current_organization(
    db: AsyncSession,
    organization_id: uuid.UUID,
) -> Organization | None:
    return await repository.get_organization(db, organization_id=organization_id)
