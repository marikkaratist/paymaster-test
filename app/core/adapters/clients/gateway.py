import asyncio
import random

from core.config import Config
from core.entities import Payment


class EmulatedPaymentGateway:
    """Эмуляция внешнего платёжного шлюза: 2-5 сек, 90% успех."""

    def __init__(self, config: Config) -> None:
        self._min_delay = config.gateway_min_delay
        self._max_delay = config.gateway_max_delay
        self._success_rate = config.gateway_success_rate

    async def charge(self, payment: Payment) -> bool:
        await asyncio.sleep(random.uniform(self._min_delay, self._max_delay))
        return random.random() < self._success_rate
