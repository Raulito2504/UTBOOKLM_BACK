from collections.abc import Awaitable, Callable
from typing import Any


EventHandler = Callable[[str, dict[str, Any]], Awaitable[None] | None]


class EventPublisher:
    def __init__(self) -> None:
        self._handlers: list[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        for handler in self._handlers:
            result = handler(event_type, payload)
            if result is not None:
                await result


publisher = EventPublisher()
