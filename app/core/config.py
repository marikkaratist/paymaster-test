import os
from dataclasses import dataclass


@dataclass(kw_only=True, slots=True)
class Config:
    log_level: str = os.environ['LOG_LEVEL']
    postgres_dsn: str = os.environ['POSTGRES_DSN']
    rabbitmq_dsn: str = os.environ['RABBITMQ_DSN']
    api_key: str = os.environ['API_KEY']

    exchange_name: str = os.environ['EXCHANGE_NAME']
    queue_name: str = os.environ['QUEUE_NAME']
    dlq_name: str = os.environ['DLQ_NAME']
    retry_max_attempts: int = int(os.environ['RETRY_MAX_ATTEMPTS'])
    retry_base_delay_ms: int = int(os.environ['RETRY_BASE_DELAY_MS'])

    gateway_min_delay: float = float(os.environ['GATEWAY_MIN_DELAY'])
    gateway_max_delay: float = float(os.environ['GATEWAY_MAX_DELAY'])
    gateway_success_rate: float = float(os.environ['GATEWAY_SUCCESS_RATE'])

    webhook_timeout: float = float(os.environ['WEBHOOK_TIMEOUT'])

    relay_batch_size: int = int(os.environ['RELAY_BATCH_SIZE'])
    relay_poll_interval: float = float(os.environ['RELAY_POLL_INTERVAL'])
