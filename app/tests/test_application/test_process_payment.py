import pytest

from core.application.process_payment.usecases import ProcessPayment
from core.entities import Payment, PaymentStatus
from core.exceptions import WebhookDeliveryError
from tests.test_application.conftest import FakeGateway, FakeNotifier, FakePaymentRepo, FakeUOW


@pytest.mark.parametrize(('charged', 'expected'), [(True, PaymentStatus.SUCCEEDED), (False, PaymentStatus.FAILED)])
async def test_sets_status_and_notifies(
    uow: FakeUOW,
    payments: FakePaymentRepo,
    pending_payment: Payment,
    *,
    charged: bool,
    expected: PaymentStatus,
) -> None:
    notifier = FakeNotifier()
    await ProcessPayment(uow, payments, FakeGateway(charged), notifier)(pending_payment.id)

    assert payments.items[pending_payment.id].status == expected
    assert payments.items[pending_payment.id].processed_at is not None
    assert [p.status for p in notifier.sent] == [expected]


async def test_webhook_failure_keeps_final_status_and_retry_only_resends(
    uow: FakeUOW, payments: FakePaymentRepo, pending_payment: Payment
) -> None:
    gateway = FakeGateway(True)
    with pytest.raises(WebhookDeliveryError):
        await ProcessPayment(uow, payments, gateway, FakeNotifier(fail=True))(pending_payment.id)
    assert payments.items[pending_payment.id].status == PaymentStatus.SUCCEEDED

    notifier = FakeNotifier()
    await ProcessPayment(uow, payments, gateway, notifier)(pending_payment.id)

    assert gateway.calls == 1  # шлюз второй раз не дёргаем
    assert len(notifier.sent) == 1


async def test_unknown_payment_is_skipped(uow: FakeUOW, payments: FakePaymentRepo) -> None:
    import uuid

    notifier = FakeNotifier()
    await ProcessPayment(uow, payments, FakeGateway(), notifier)(uuid.uuid4())
    assert notifier.sent == []
