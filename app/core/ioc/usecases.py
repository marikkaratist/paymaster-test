from dishka import Provider, Scope, provide

from core.application.common_interfaces import UnitOfWork
from core.application.create_payment.usecases import CreatePayment
from core.application.get_payment import GetPayment
from core.application.process_payment.usecases import ProcessPayment
from core.application.relay_outbox.interfaces import EventPublisher, OutboxRepo
from core.application.relay_outbox.usecases import RelayOutbox
from core.config import Config


class CreatePaymentProvider(Provider):
    create_payment = provide(CreatePayment, scope=Scope.REQUEST)


class GetPaymentProvider(Provider):
    get_payment = provide(GetPayment, scope=Scope.REQUEST)


class ProcessPaymentProvider(Provider):
    process_payment = provide(ProcessPayment, scope=Scope.REQUEST)


class RelayOutboxProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def relay_outbox(
        self,
        uow: UnitOfWork,
        outbox: OutboxRepo,
        publisher: EventPublisher,
        config: Config,
    ) -> RelayOutbox:
        return RelayOutbox(uow, outbox, publisher, config.relay_batch_size)
