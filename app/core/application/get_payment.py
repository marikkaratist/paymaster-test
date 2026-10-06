import uuid
from typing import Protocol

from core.entities import Payment
from core.exceptions import NotFoundError


class GetPaymentRepo(Protocol):
    async def get(self, payment_id: uuid.UUID) -> Payment | None: ...


class GetPayment:
    def __init__(self, payments: GetPaymentRepo) -> None:
        self._payments = payments

    def __str__(self) -> str:
        return 'get payment'

    async def __call__(self, payment_id: uuid.UUID) -> Payment:
        payment = await self._payments.get(payment_id)
        if payment is None:
            raise NotFoundError(f'Платёж {payment_id} не найден')
        return payment
