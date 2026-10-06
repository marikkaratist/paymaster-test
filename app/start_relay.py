import asyncio

from dishka import make_async_container
from faststream.rabbit import RabbitBroker

from core.adapters.clients.amqp import Topology
from core.application.relay_outbox.usecases import RelayOutbox
from core.config import Config
from core.ioc import AMQPProvider, AppProvider, PostgresProvider, RelayOutboxProvider, RepoProvider
from core.logger import get_logger, setup_logging

logger = get_logger('relay')


async def main() -> None:
    config = Config()
    setup_logging(config.log_level)
    container = make_async_container(
        AppProvider(),
        PostgresProvider(),
        RepoProvider(),
        AMQPProvider(),
        RelayOutboxProvider(),
        context={Config: config},
    )
    broker = await container.get(RabbitBroker)
    await broker.start()
    await (await container.get(Topology)).declare(broker)
    try:
        while True:
            try:
                async with container() as request_container:
                    relayed = await (await request_container.get(RelayOutbox))()
            except Exception:
                logger.exception('relay iteration failed')
                relayed = 0
            if not relayed:
                await asyncio.sleep(config.relay_poll_interval)
    finally:
        await container.close()


if __name__ == '__main__':
    asyncio.run(main())
