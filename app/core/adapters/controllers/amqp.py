import uuid
from typing import Any

from dishka.integrations.faststream import FromDishka
from faststream.rabbit import RabbitBroker, RabbitMessage
from pydantic import BaseModel

from core.adapters.clients.amqp import RETRY_HEADER, AMQPRetryScheduler, Topology
from core.application.process_payment.usecases import ProcessPayment
from core.logger import get_logger

logger = get_logger(__name__)


class PaymentMessage(BaseModel):
    payment_id: uuid.UUID


def register_subscribers(broker: RabbitBroker, topology: Topology) -> None:
    @broker.subscriber(topology.queue, topology.exchange, retry=False)
    async def process_payment(
        body: PaymentMessage,
        message: RabbitMessage,
        usecase: FromDishka[ProcessPayment],
        scheduler: FromDishka[AMQPRetryScheduler],
    ) -> None:
        """Любая ошибка → сообщение уходит в retry-очередь/DLQ, исходное ack'ается."""
        attempt = int((message.headers or {}).get(RETRY_HEADER, 0)) + 1
        try:
            await usecase(body.payment_id)
        except Exception:
            logger.exception('processing failed', payment_id=str(body.payment_id), attempt=attempt)
            payload: dict[str, Any] = {'payment_id': str(body.payment_id)}
            target = await scheduler.retry_or_dead_letter(payload, attempt, message.message_id)
            logger.warning('message rescheduled', target=target, attempt=attempt)
