from core.application.common_interfaces import UnitOfWork
from core.application.relay_outbox.interfaces import EventPublisher, OutboxRepo
from core.logger import get_logger

logger = get_logger(__name__)


class RelayOutbox:
    """Публикует pending-события из outbox. Возвращает число опубликованных событий.

    Строки блокируются FOR UPDATE SKIP LOCKED — несколько relay не публикуют одно событие дважды.
    Если публикация упала, транзакция откатывается и событие остаётся pending (at-least-once).
    """

    def __init__(self, uow: UnitOfWork, outbox: OutboxRepo, publisher: EventPublisher, batch_size: int) -> None:
        self._uow = uow
        self._outbox = outbox
        self._publisher = publisher
        self._batch_size = batch_size

    def __str__(self) -> str:
        return 'rely outbox'

    async def __call__(self) -> int:
        published = 0
        async with self._uow:
            for event in await self._outbox.fetch_pending_for_update(self._batch_size):
                await self._publisher.publish(event)
                await self._outbox.mark_published(event)
                published += 1
        if published:
            logger.info('outbox relayed', count=published)
        return published
