import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Notification, WebhookEvent


async def create_webhook_event(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any],
) -> WebhookEvent:
    event = WebhookEvent(
        organization_id=organization_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(event)
    await db.flush()
    return event


async def list_webhook_events(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
) -> list[WebhookEvent]:
    result = await db.execute(
        select(WebhookEvent)
        .where(WebhookEvent.organization_id == organization_id)
        .order_by(WebhookEvent.created_at.desc()),
    )
    return list(result.scalars().all())


async def create_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    title: str,
    body: str,
    payload: dict[str, Any] | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        body=body,
        payload=payload,
    )
    db.add(notification)
    await db.flush()
    return notification
