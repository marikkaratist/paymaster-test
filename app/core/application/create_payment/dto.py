from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from core.entities import Currency


@dataclass(frozen=True, slots=True)
class CreatePaymentDTO:
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    webhook_url: str
    idempotency_key: str
