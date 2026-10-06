from typing import Protocol

from core.entities import OutboxEvent


class OutboxRepo(Protocol):
    async def fetch_pending_for_update(self, limit: int) -> list[OutboxEvent]: ...

    async def mark_published(self, event: OutboxEvent) -> None: ...


class EventPublisher(Protocol):
    async def publish(self, event: OutboxEvent) -> None:
        """Публикует событие с подтверждением брокера (publisher confirms)."""
