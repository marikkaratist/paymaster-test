from collections.abc import AsyncIterator

import httpx
from dishka import Provider, Scope, from_context, provide
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from core.adapters.clients.amqp import AMQPEventPublisher, AMQPRetryScheduler, Topology
from core.adapters.clients.gateway import EmulatedPaymentGateway
from core.adapters.clients.http_webhook import HttpWebhookNotifier
from core.adapters.repos import PostgresOutboxRepo, PostgresPaymentRepo
from core.adapters.uow import SQLAlchemyUOW
from core.application.common_interfaces import UnitOfWork
from core.application.create_payment.interfaces import CreatePaymentRepo, OutboxWriter
from core.application.get_payment import GetPaymentRepo
from core.application.process_payment.interfaces import PaymentGateway, ProcessPaymentRepo, WebhookNotifier
from core.application.relay_outbox.interfaces import EventPublisher, OutboxRepo
from core.config import Config
from core.drivers.db.engine import make_engine, make_sessionmaker


class AppProvider(Provider):
    scope = Scope.APP

    config = from_context(provides=Config)


class PostgresProvider(Provider):
    @provide(scope=Scope.APP)
    async def engine(self, config: Config) -> AsyncIterator[AsyncEngine]:
        engine = make_engine(config.postgres_dsn)
        yield engine
        await engine.dispose()

    @provide(scope=Scope.APP)
    def sessionmaker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return make_sessionmaker(engine)

    @provide(scope=Scope.REQUEST)
    async def session(self, maker: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
        async with maker() as session:
            yield session

    uow = provide(SQLAlchemyUOW, provides=UnitOfWork, scope=Scope.REQUEST)
    payment_repo = provide(PostgresPaymentRepo, scope=Scope.REQUEST)
    outbox_repo = provide(PostgresOutboxRepo, scope=Scope.REQUEST)


class RepoProvider(Provider):
    """Один класс-адаптер реализует несколько Protocol-портов."""

    scope = Scope.REQUEST

    @provide
    def create_payment_repo(self, repo: PostgresPaymentRepo) -> CreatePaymentRepo:
        return repo

    @provide
    def get_payment_repo(self, repo: PostgresPaymentRepo) -> GetPaymentRepo:
        return repo

    @provide
    def process_payment_repo(self, repo: PostgresPaymentRepo) -> ProcessPaymentRepo:
        return repo

    @provide
    def outbox_writer(self, repo: PostgresOutboxRepo) -> OutboxWriter:
        return repo

    @provide
    def outbox_repo(self, repo: PostgresOutboxRepo) -> OutboxRepo:
        return repo


class AMQPProvider(Provider):
    @provide(scope=Scope.APP)
    def topology(self, config: Config) -> Topology:
        return Topology(config)

    @provide(scope=Scope.APP)
    async def broker(self, config: Config, topology: Topology) -> AsyncIterator[RabbitBroker]:
        broker = RabbitBroker(config.rabbitmq_dsn)
        yield broker
        await broker.close()

    event_publisher = provide(AMQPEventPublisher, provides=EventPublisher, scope=Scope.APP)
    retry_scheduler = provide(AMQPRetryScheduler, scope=Scope.APP)


class ClientsProvider(Provider):
    @provide(scope=Scope.APP)
    async def http_client(self, config: Config) -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient(timeout=config.webhook_timeout) as client:
            yield client

    gateway = provide(EmulatedPaymentGateway, provides=PaymentGateway, scope=Scope.APP)
    notifier = provide(HttpWebhookNotifier, provides=WebhookNotifier, scope=Scope.APP)
