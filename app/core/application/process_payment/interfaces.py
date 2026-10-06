import uuid
from datetime import datetime
from typing import Protocol

from core.entities import Payment, PaymentStatus


class ProcessPaymentRepo(Protocol):
    async def get(self, payment_id: uuid.UUID) -> Payment | None: ...

    async def get_for_update(self, payment_id: uuid.UUID) -> Payment | None: ...

    async def set_result(self, payment_id: uuid.UUID, status: PaymentStatus, processed_at: datetime) -> None: ...


class PaymentGateway(Protocol):
    async def charge(self, payment: Payment) -> bool:
        """Возвращает True, если платёж успешно проведён."""


class WebhookNotifier(Protocol):
    async def notify(self, payment: Payment) -> None:
        """Бросает WebhookDeliveryError, если доставить не удалось."""
