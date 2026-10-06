import uuid
from datetime import datetime
from decimal import Decimal
from typing import Self

import pytest

from core.entities import Currency, OutboxEvent, OutboxStatus, Payment, PaymentStatus, utcnow
from core.exceptions import WebhookDeliveryError


class FakeUOW:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: object, *args: object) -> None:
        if exc_type is None:
            self.commits += 1
        else:
            self.rollbacks += 1


class FakePaymentRepo:
    def __init__(self) -> None:
        self.items: dict[uuid.UUID, Payment] = {}

    async def add_if_absent(self, payment: Payment) -> bool:
        if any(p.idempotency_key == payment.idempotency_key for p in self.items.values()):
            return False
        self.items[payment.id] = payment
        return True

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        return next((p for p in self.items.values() if p.idempotency_key == key), None)

    async def get(self, payment_id: uuid.UUID) -> Payment | None:
        return self.items.get(payment_id)

    get_for_update = get

    async def set_result(self, payment_id: uuid.UUID, status: PaymentStatus, processed_at: datetime) -> None:
        self.items[payment_id].status = status
        self.items[payment_id].processed_at = processed_at


class FakeOutbox:
    def __init__(self) -> None:
        self.events: list[OutboxEvent] = []

    async def add(self, event: OutboxEvent) -> None:
        self.events.append(event)

    async def fetch_pending_for_update(self, limit: int) -> list[OutboxEvent]:
        return [e for e in self.events if e.status == OutboxStatus.PENDING][:limit]

    async def mark_published(self, event: OutboxEvent) -> None:
        event.status = OutboxStatus.PUBLISHED
        event.published_at = utcnow()


class FakeGateway:
    def __init__(self, result: bool = True) -> None:
        self.result = result
        self.calls = 0

    async def charge(self, payment: Payment) -> bool:
        self.calls += 1
        return self.result


class FakeNotifier:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.sent: list[Payment] = []

    async def notify(self, payment: Payment) -> None:
        if self.fail:
            raise WebhookDeliveryError('boom')
        self.sent.append(payment)


class FakePublisher:
    def __init__(self, fail_on: int | None = None) -> None:
        self.published: list[OutboxEvent] = []
        self.fail_on = fail_on

    async def publish(self, event: OutboxEvent) -> None:
        if self.fail_on is not None and len(self.published) == self.fail_on:
            raise RuntimeError('broker down')
        self.published.append(event)


@pytest.fixture
def uow() -> FakeUOW:
    return FakeUOW()


@pytest.fixture
def payments() -> FakePaymentRepo:
    return FakePaymentRepo()


@pytest.fixture
def outbox() -> FakeOutbox:
    return FakeOutbox()


@pytest.fixture
def pending_payment(payments: FakePaymentRepo) -> Payment:
    payment = Payment(
        amount=Decimal('10.00'),
        currency=Currency.RUB,
        description='test',
        metadata={},
        idempotency_key='k-1',
        request_hash='h',
        webhook_url='http://localhost/hook',
    )
    payments.items[payment.id] = payment
    return payment
