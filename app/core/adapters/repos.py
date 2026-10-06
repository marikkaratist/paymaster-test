import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.drivers.db.models import OutboxModel, PaymentModel
from core.entities import Currency, OutboxEvent, OutboxStatus, Payment, PaymentStatus, utcnow
from core.exceptions import AdapterError


def to_payment(model: PaymentModel) -> Payment:
    return Payment(
        id=model.id,
        amount=model.amount,
        currency=Currency(model.currency),
        description=model.description,
        metadata=model.metadata_,
        status=PaymentStatus(model.status),
        idempotency_key=model.idempotency_key,
        request_hash=model.request_hash,
        webhook_url=model.webhook_url,
        created_at=model.created_at,
        processed_at=model.processed_at,
    )


def to_outbox_event(model: OutboxModel) -> OutboxEvent:
    return OutboxEvent(
        id=model.id,
        event_type=model.event_type,
        payload=model.payload,
        status=OutboxStatus(model.status),
        created_at=model.created_at,
        published_at=model.published_at,
    )


class PostgresPaymentRepo:
    """Реализует все порты платежей; транзакцией управляет UoW."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_if_absent(self, payment: Payment) -> bool:
        stmt = (
            insert(PaymentModel)
            .values(
                id=payment.id,
                amount=payment.amount,
                currency=payment.currency.value,
                description=payment.description,
                metadata_=payment.metadata,
                status=payment.status.value,
                idempotency_key=payment.idempotency_key,
                request_hash=payment.request_hash,
                webhook_url=payment.webhook_url,
                created_at=payment.created_at,
            )
            .on_conflict_do_nothing(index_elements=[PaymentModel.idempotency_key])
            .returning(PaymentModel.id)
        )
        try:
            return (await self._session.execute(stmt)).scalar_one_or_none() is not None
        except SQLAlchemyError as exc:
            raise AdapterError('Не удалось сохранить платёж') from exc

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        model = (
            await self._session.execute(select(PaymentModel).where(PaymentModel.idempotency_key == key))
        ).scalar_one_or_none()
        return to_payment(model) if model else None

    async def get(self, payment_id: uuid.UUID) -> Payment | None:
        model = await self._session.get(PaymentModel, payment_id)
        return to_payment(model) if model else None

    async def get_for_update(self, payment_id: uuid.UUID) -> Payment | None:
        stmt = select(PaymentModel).where(PaymentModel.id == payment_id).with_for_update()
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_payment(model) if model else None

    async def set_result(self, payment_id: uuid.UUID, status: PaymentStatus, processed_at: datetime) -> None:
        await self._session.execute(
            update(PaymentModel)
            .where(PaymentModel.id == payment_id)
            .values(status=status.value, processed_at=processed_at),
        )


class PostgresOutboxRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: OutboxEvent) -> None:
        self._session.add(
            OutboxModel(
                id=event.id,
                event_type=event.event_type,
                payload=event.payload,
                status=event.status.value,
                created_at=event.created_at,
            ),
        )
        await self._session.flush()

    async def fetch_pending_for_update(self, limit: int) -> list[OutboxEvent]:
        stmt = (
            select(OutboxModel)
            .where(OutboxModel.status == OutboxStatus.PENDING.value)
            .order_by(OutboxModel.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return [to_outbox_event(m) for m in (await self._session.execute(stmt)).scalars()]

    async def mark_published(self, event: OutboxEvent) -> None:
        await self._session.execute(
            update(OutboxModel)
            .where(OutboxModel.id == event.id)
            .values(status=OutboxStatus.PUBLISHED.value, published_at=utcnow()),
        )
