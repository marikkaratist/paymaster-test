import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from core.entities import Currency, PaymentStatus


class CreatePaymentRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    amount: Annotated[Decimal, Field(gt=0, max_digits=15, decimal_places=2)]
    currency: Currency
    description: str = Field(min_length=1, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: AnyHttpUrl


class CreatePaymentResponse(BaseModel):
    payment_id: uuid.UUID
    status: PaymentStatus
    created_at: datetime


class PaymentResponse(BaseModel):
    payment_id: uuid.UUID
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    status: PaymentStatus
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None


class ErrorResponse(BaseModel):
    code: str
    message: str
