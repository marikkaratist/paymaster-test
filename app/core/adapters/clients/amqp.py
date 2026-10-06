import uuid
from typing import Any

from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue
from faststream.rabbit.schemas import ExchangeType

from core.config import Config
from core.entities import OutboxEvent

RETRY_HEADER = 'x-retry-count'


class Topology:
    """exchange payments (direct) → payments.new; retry-очереди с TTL (экспоненциальный backoff) → payments.dlq."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.exchange = RabbitExchange(config.exchange_name, type=ExchangeType.DIRECT, durable=True)
        self.queue = RabbitQueue(
            config.queue_name,
            durable=True,
            routing_key=config.queue_name,
        )
        self.dlq = RabbitQueue(config.dlq_name, durable=True, routing_key=config.dlq_name)
        # попытки 1..N-1 завершаются retry-очередью; N-я неудача уходит в DLQ
        self.retry_queues = [
            RabbitQueue(
                self.retry_name(level),
                durable=True,
                routing_key=self.retry_name(level),
                arguments={
                    'x-message-ttl': config.retry_base_delay_ms * 2**level,
                    'x-dead-letter-exchange': config.exchange_name,
                    'x-dead-letter-routing-key': config.queue_name,
                },
            )
            for level in range(config.retry_max_attempts - 1)
        ]

    def retry_name(self, level: int) -> str:
        return f'{self.config.queue_name}.retry.{level + 1}'

    async def declare(self, broker: RabbitBroker) -> None:
        exchange = await broker.declare_exchange(self.exchange)
        for queue in (self.queue, self.dlq, *self.retry_queues):
            declared = await broker.declare_queue(queue)
            await declared.bind(exchange, routing_key=queue.routing)


class AMQPEventPublisher:
    def __init__(self, broker: RabbitBroker, topology: Topology) -> None:
        self._broker = broker
        self._topology = topology

    async def publish(self, event: OutboxEvent) -> None:
        await self._broker.publish(
            event.payload,
            exchange=self._topology.exchange,
            routing_key=self._topology.queue.routing,
            message_id=str(event.id),
            persist=True,
            timeout=10,
        )


class AMQPRetryScheduler:
    def __init__(self, broker: RabbitBroker, topology: Topology) -> None:
        self._broker = broker
        self._topology = topology

    async def retry_or_dead_letter(self, body: dict[str, Any], attempt: int, message_id: str | None) -> str:
        """attempt — номер только что проваленной попытки (с 1). Возвращает куда ушло сообщение."""
        max_attempts = self._topology.config.retry_max_attempts
        target = self._topology.config.dlq_name if attempt >= max_attempts else self._topology.retry_name(attempt - 1)
        await self._broker.publish(
            body,
            exchange=self._topology.exchange,
            routing_key=target,
            headers={RETRY_HEADER: attempt},
            message_id=message_id or str(uuid.uuid4()),
            persist=True,
        )
        return target
