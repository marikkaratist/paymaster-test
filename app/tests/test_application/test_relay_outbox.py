import pytest

from core.application.relay_outbox.usecases import RelayOutbox
from core.entities import OutboxEvent, OutboxStatus
from tests.test_application.conftest import FakeOutbox, FakePublisher, FakeUOW


def seed(outbox: FakeOutbox, count: int) -> None:
    outbox.events = [OutboxEvent(event_type='payments.new', payload={'payment_id': str(i)}) for i in range(count)]


async def test_publishes_and_marks_published(uow: FakeUOW, outbox: FakeOutbox) -> None:
    seed(outbox, 3)
    publisher = FakePublisher()

    assert await RelayOutbox(uow, outbox, publisher, batch_size=10)() == 3
    assert len(publisher.published) == 3
    assert all(e.status == OutboxStatus.PUBLISHED for e in outbox.events)
    assert await RelayOutbox(uow, outbox, publisher, batch_size=10)() == 0


async def test_respects_batch_size(uow: FakeUOW, outbox: FakeOutbox) -> None:
    seed(outbox, 5)
    assert await RelayOutbox(uow, outbox, FakePublisher(), batch_size=2)() == 2


async def test_publish_failure_rolls_back_transaction(uow: FakeUOW, outbox: FakeOutbox) -> None:
    seed(outbox, 2)
    with pytest.raises(RuntimeError):
        await RelayOutbox(uow, outbox, FakePublisher(fail_on=1), batch_size=10)()
    assert uow.rollbacks == 1
