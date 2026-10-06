from typing import Protocol

from core.entities import OutboxEvent, Payment


class CreatePaymentRepo(Protocol):
    async def add_if_absent(self, payment: Payment) -> bool:
        """Вставляет платёж; False, если платёж с таким idempotency_key уже существует."""

    async def get_by_idempotency_key(self, key: str) -> Payment | None: ...


class OutboxWriter(Protocol):
    async def add(self, event: OutboxEvent) -> None: ...
