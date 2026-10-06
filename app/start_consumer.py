import asyncio

from dishka import make_async_container
from dishka_faststream import setup_dishka
from faststream import FastStream
from faststream.rabbit import RabbitBroker

from core.adapters.clients.amqp import Topology
from core.adapters.controllers.amqp import register_subscribers
from core.config import Config
from core.ioc import (
    AMQPProvider,
    AppProvider,
    ClientsProvider,
    PostgresProvider,
    ProcessPaymentProvider,
    RepoProvider,
)
from core.logger import setup_logging


async def main() -> None:
    config = Config()
    setup_logging(config.log_level)
    container = make_async_container(
        AppProvider(),
        PostgresProvider(),
        RepoProvider(),
        AMQPProvider(),
        ClientsProvider(),
        ProcessPaymentProvider(),
        context={Config: config},
    )
    broker = await container.get(RabbitBroker)
    topology = await container.get(Topology)
    register_subscribers(broker, topology)

    app = FastStream(broker)

    @app.after_startup
    async def declare_topology() -> None:
        await topology.declare(broker)

    setup_dishka(container, app, auto_inject=True)
    await app.run()


if __name__ == '__main__':
    asyncio.run(main())
