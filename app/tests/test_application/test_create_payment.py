from decimal import Decimal

import pytest

from core.application.create_payment.dto import CreatePaymentDTO
from core.application.create_payment.usecases import CreatePayment
from core.entities import Currency
from core.exceptions import IdempotencyConflictError
from tests.test_application.conftest import FakeOutbox, FakePaymentRepo, FakeUOW


def make_dto(key: str = 'key-1', amount: str = '100.00') -> CreatePaymentDTO:
    return CreatePaymentDTO(
        amount=Decimal(amount),
        currency=Currency.USD,
        description='order',
        metadata={'order_id': 1},
        webhook_url='http://localhost/hook',
        idempotency_key=key,
    )


async def test_creates_payment_and_outbox_event_in_one_transaction(
    uow: FakeUOW, payments: FakePaymentRepo, outbox: FakeOutbox
) -> None:
    payment = await CreatePayment(uow, payments, outbox)(make_dto())

    assert payments.items[payment.id] is payment
    assert [e.payload for e in outbox.events] == [{'payment_id': str(payment.id)}]
    assert (uow.commits, uow.rollbacks) == (1, 0)


async def test_same_key_same_body_returns_existing_without_new_event(
    uow: FakeUOW, payments: FakePaymentRepo, outbox: FakeOutbox
) -> None:
    usecase = CreatePayment(uow, payments, outbox)
    first = await usecase(make_dto())
    second = await usecase(make_dto())

    assert second.id == first.id
    assert len(payments.items) == 1
    assert len(outbox.events) == 1


async def test_same_key_other_body_raises_conflict(uow: FakeUOW, payments: FakePaymentRepo, outbox: FakeOutbox) -> None:
    usecase = CreatePayment(uow, payments, outbox)
    await usecase(make_dto())

    with pytest.raises(IdempotencyConflictError):
        await usecase(make_dto(amount='999.00'))
    assert len(outbox.events) == 1
