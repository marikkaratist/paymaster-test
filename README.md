# Paymaster — асинхронный сервис процессинга платежей

FastAPI + Pydantic v2, SQLAlchemy 2 (async), PostgreSQL, RabbitMQ (FastStream), Alembic, Dishka, Docker Compose.

## Архитектура

```
POST /api/v1/payments ──► app ──(1 транзакция)──► payments + outbox (PostgreSQL)
                                                         │
                         relay (SELECT … FOR UPDATE SKIP LOCKED) ◄┘
                              │ publish (confirms) → exchange `payments` → `payments.new`
                              ▼
                         consumer: эмуляция шлюза (2–5 c, 90% успех) → статус в БД → webhook
                              │ ошибка
                              ▼
          payments.new.retry.1 (TTL 2 c) → payments.new.retry.2 (TTL 4 c) → payments.dlq
```

Слои:

```
app/core/
├── entities.py, exceptions.py, config.py   # домен, ошибки, настройки
├── application/                            # usecases + Protocol-порты
├── adapters/                               # repos, uow, AMQP/HTTP-клиенты, контроллеры
├── drivers/db/                             # engine, модели SQLAlchemy
└── ioc/                                    # провайдеры Dishka
app/main.py            # API (сервис app)
app/start_consumer.py  # consumer
app/start_relay.py     # outbox relay
```

### Гарантии
- **Outbox**: платёж и событие пишутся в одной транзакции; relay публикует события с publisher confirms и помечает
  `published` в той же транзакции, где держит блокировку строк (`SKIP LOCKED` — relay можно масштабировать).
  Доставка at-least-once, дубликаты безопасны из-за идемпотентного consumer'а.
- **Idempotency-Key**: уникальный индекс + `INSERT … ON CONFLICT DO NOTHING`. Повтор с тем же телом → тот же
  платёж (202, без нового события); тот же ключ с другим телом → `409`.
- **Consumer идемпотентен**: финальный статус не перезаписывается; при повторе сообщения повторяется только webhook.
- **Retry**: 3 попытки, задержки 2 c / 4 c (экспоненциально, `RETRY_BASE_DELAY_MS`), после третьей неудачи
  сообщение попадает в `payments.dlq`.

## Процессы

Один образ, три процесса — каждый запускается отдельным контейнером с собственной командой:

| Сервис     | Команда                    | Назначение |
|------------|----------------------------|------------|
| `app`      | `python main.py`           | HTTP API. В одной транзакции пишет платёж и событие в `payments` и `outbox`; с RabbitMQ не работает. |
| `relay`    | `python start_relay.py`    | Outbox relay. Раз в `RELAY_POLL_INTERVAL` берёт `pending`-события (`FOR UPDATE SKIP LOCKED`), публикует в `payments.new` и помечает `published`. |
| `consumer` | `python start_consumer.py` | Единственный обработчик `payments.new`: эмуляция шлюза → статус в БД → webhook; при ошибке — retry-очереди и DLQ. |

Зачем разделены:
- **Без `relay` платёж навсегда остаётся `pending`** — события лежат в `outbox`, и их никто не публикует.
- **Без `consumer` сообщения копятся в `payments.new`** и не обрабатываются.
- **API не зависит от брокера**: при недоступном RabbitMQ платежи принимаются, события дождутся в `outbox`.
- **Независимое масштабирование и перезапуск**: `relay` безопасно запускать в нескольких экземплярах (`SKIP LOCKED`),
  падение одного процесса не останавливает остальные (`restart: always`).

## Запуск

```bash
cp .env.example .env   # при необходимости поменять API_KEY
docker compose up -d --build                  # postgres, rabbitmq, app, consumer, relay
docker compose exec app alembic upgrade head  # миграции (вручную, после старта)
```

Пока миграции не применены, `consumer` и `relay` пишут ошибки подключения к таблицам — после `alembic upgrade head`
перезапуск не нужен.

API: http://localhost:8000 (Swagger — `/docs`), RabbitMQ UI: http://localhost:15672 (guest/guest).

## Примеры

```bash
# создание платежа
curl -i -X POST localhost:8000/api/v1/payments \
  -H 'X-API-Key: secret-api-key' -H 'Idempotency-Key: order-1' -H 'Content-Type: application/json' \
  -d '{"amount": "100.50", "currency": "RUB", "description": "Order #1", "metadata": {"order_id": 1},
       "webhook_url": "https://webhook.site/<your-id>"}'
# → 202 {"payment_id": "...", "status": "pending", "created_at": "..."}

# повтор с тем же ключом → тот же payment_id
# получение
curl -H 'X-API-Key: secret-api-key' localhost:8000/api/v1/payments/<payment_id>
```

Webhook (POST на `webhook_url`):
```json
{"payment_id": "...", "status": "succeeded", "amount": "100.50", "currency": "RUB", "processed_at": "..."}
```

Проверка retry/DLQ: укажите недоступный `webhook_url` (например `http://localhost:9/hook`) — в логах consumer будут
3 попытки, затем сообщение появится в очереди `payments.dlq`.

Коды ошибок: `401` — нет/неверный `X-API-Key`; `422` — невалидное тело или нет `Idempotency-Key`;
`404` — платёж не найден; `409` — конфликт Idempotency-Key.

## Тесты и линтеры

```bash
docker compose exec app pytest                # тесты в контейнере (нужен postgres из compose)

cd app
set -a; . ../.env; set +a                     # локально .env нужно экспортировать вручную
uv run ruff check . && uv run ruff format --check . && uv run mypy .
```
