import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DECIMAL, DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.drivers.db.base import Base


class PaymentModel(Base):
    __tablename__ = 'payments'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2))
    currency: Mapped[str] = mapped_column(String(3))
    description: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column('metadata', JSONB, server_default=text("'{}'::jsonb"))
    status: Mapped[str] = mapped_column(String(16), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    webhook_url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OutboxModel(Base):
    __tablename__ = 'outbox'
    __table_args__ = (Index('ix_outbox_pending', 'created_at', postgresql_where=text("status = 'pending'")),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
