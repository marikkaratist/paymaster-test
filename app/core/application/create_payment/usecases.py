import hashlib
import json

from core.application.common_interfaces import UnitOfWork
from core.application.create_payment.dto import CreatePaymentDTO
from core.application.create_payment.interfaces import CreatePaymentRepo, OutboxWriter
from core.entities import OutboxEvent, Payment
from core.exceptions import IdempotencyConflictError
from core.logger import get_logger

logger = get_logger(__name__)

PAYMENT_CREATED_EVENT = 'payments.new'


def hash_request(dto: CreatePaymentDTO) -> str:
    body = {
        'amount': str(dto.amount),
        'currency': dto.currency.value,
        'description': dto.description,
        'metadata': dto.metadata,
        'webhook_url': dto.webhook_url,
    }
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


class CreatePayment:
    def __init__(self, uow: UnitOfWork, payments: CreatePaymentRepo, outbox: OutboxWriter) -> None:
        self._uow = uow
        self._payments = payments
        self._outbox = outbox

    def __str__(self) -> str:
        return 'create payment'

    async def __call__(self, dto: CreatePaymentDTO) -> Payment:
        request_hash = hash_request(dto)
        payment = Payment(
            amount=dto.amount,
            currency=dto.currency,
            description=dto.description,
            metadata=dto.metadata,
            idempotency_key=dto.idempotency_key,
            request_hash=request_hash,
            webhook_url=dto.webhook_url,
        )
        async with self._uow:
            if await self._payments.add_if_absent(payment):
                await self._outbox.add(
                    OutboxEvent(event_type=PAYMENT_CREATED_EVENT, payload={'payment_id': str(payment.id)}),
                )
                logger.info('payment created', payment_id=str(payment.id))
                return payment

            existing = await self._payments.get_by_idempotency_key(dto.idempotency_key)
            if existing is None or existing.request_hash != request_hash:
                raise IdempotencyConflictError('Idempotency-Key уже использован с другим телом запроса')
            logger.info('idempotent replay', payment_id=str(existing.id))
            return existing
