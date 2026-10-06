from core.adapters.clients.amqp import Topology
from core.config import Config


def test_retry_queues_have_exponential_ttl() -> None:
    topology = Topology(Config(retry_max_attempts=3, retry_base_delay_ms=2000))

    assert [q.name for q in topology.retry_queues] == ['payments.new.retry.1', 'payments.new.retry.2']
    assert [q.arguments['x-message-ttl'] for q in topology.retry_queues] == [2000, 4000]
