import uuid

from core.application.common_interfaces import UnitOfWork
from core.application.process_payment.interfaces import PaymentGateway, ProcessPaymentRepo, WebhookNotifier
from core.entities import Payment, PaymentStatus, utcnow
from core.logger import get_logger

logger = get_logger(__name__)


class ProcessPayment:
    """Эмуляция обработки платежа + webhook.

    Идемпотентен: финальный статус не перезаписывается, при повторной доставке сообщения
    повторяется только отправка webhook.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        payments: ProcessPaymentRepo,
        gateway: PaymentGateway,
        notifier: WebhookNotifier,
    ) -> None:
        self._uow = uow
        self._payments = payments
        self._gateway = gateway
        self._notifier = notifier

    def __str__(self) -> str:
        return 'process payment'

    async def __call__(self, payment_id: uuid.UUID) -> None:
        async with self._uow:
            payment = await self._payments.get(payment_id)
        if payment is None:
            logger.warning('payment not found, skip', payment_id=str(payment_id))
            return

        if not payment.is_finished:
            payment = await self._finish(payment)

        await self._notifier.notify(payment)
        logger.info('payment processed', payment_id=str(payment_id), status=payment.status.value)

    async def _finish(self, payment: Payment) -> Payment:
        succeeded = await self._gateway.charge(payment)  # долгая операция — вне транзакции
        status = PaymentStatus.SUCCEEDED if succeeded else PaymentStatus.FAILED
        async with self._uow:
            locked = await self._payments.get_for_update(payment.id)
            if locked is None or locked.is_finished:
                return locked or payment
            processed_at = utcnow()
            await self._payments.set_result(payment.id, status, processed_at)
            locked.status = status
            locked.processed_at = processed_at
            return locked
