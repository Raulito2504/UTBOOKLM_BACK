from typing import Any

from src.core.events import publisher


async def publish_notification_event(
    event_type: str,
    payload: dict[str, Any],
) -> None:
    await publisher.publish(event_type, payload)
