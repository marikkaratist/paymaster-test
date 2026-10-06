import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


def utcnow() -> datetime:
    return datetime.now(UTC)


class Currency(StrEnum):
    RUB = 'RUB'
    USD = 'USD'
    EUR = 'EUR'


class PaymentStatus(StrEnum):
    PENDING = 'pending'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'


class OutboxStatus(StrEnum):
    PENDING = 'pending'
    PUBLISHED = 'published'


@dataclass(kw_only=True, slots=True)
class Payment:
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    idempotency_key: str
    request_hash: str
    webhook_url: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = field(default_factory=utcnow)
    processed_at: datetime | None = None

    @property
    def is_finished(self) -> bool:
        return self.status != PaymentStatus.PENDING


@dataclass(kw_only=True, slots=True)
class OutboxEvent:
    event_type: str
    payload: dict[str, Any]
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: OutboxStatus = OutboxStatus.PENDING
    created_at: datetime = field(default_factory=utcnow)
    published_at: datetime | None = None
