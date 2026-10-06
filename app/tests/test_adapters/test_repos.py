from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from core.adapters.repos import PostgresOutboxRepo, PostgresPaymentRepo
from core.entities import Currency, OutboxEvent, OutboxStatus, Payment, PaymentStatus, utcnow


def make_payment(key: str = 'k') -> Payment:
    return Payment(
        amount=Decimal('12.50'),
        currency=Currency.EUR,
        description='d',
        metadata={'a': 1},
        idempotency_key=key,
        request_hash='h',
        webhook_url='http://localhost/hook',
    )


async def test_add_if_absent_is_idempotent_by_key(db_session: AsyncSession) -> None:
    repo = PostgresPaymentRepo(db_session)
    first = make_payment()

    assert await repo.add_if_absent(first) is True
    assert await repo.add_if_absent(make_payment()) is False
    stored = await repo.get_by_idempotency_key('k')
    assert stored is not None
    assert (stored.id, stored.amount, stored.metadata) == (first.id, Decimal('12.50'), {'a': 1})


async def test_set_result_updates_status(db_session: AsyncSession) -> None:
    repo = PostgresPaymentRepo(db_session)
    payment = make_payment()
    await repo.add_if_absent(payment)

    await repo.set_result(payment.id, PaymentStatus.SUCCEEDED, utcnow())
    locked = await repo.get_for_update(payment.id)

    assert locked is not None
    assert locked.status == PaymentStatus.SUCCEEDED
    assert locked.processed_at is not None


async def test_outbox_fetch_returns_only_pending_and_mark_published(db_session: AsyncSession) -> None:
    repo = PostgresOutboxRepo(db_session)
    event = OutboxEvent(event_type='payments.new', payload={'payment_id': 'x'})
    await repo.add(event)

    pending = await repo.fetch_pending_for_update(10)
    assert [e.id for e in pending] == [event.id]

    await repo.mark_published(event)
    assert await repo.fetch_pending_for_update(10) == []
    assert OutboxStatus.PUBLISHED.value == 'published'
