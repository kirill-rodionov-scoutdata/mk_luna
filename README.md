# Payments Service

Асинхронный сервис обработки платежей на FastAPI + PostgreSQL + RabbitMQ.

## Что реализовано

- `POST /api/v1/payments` — создание платежа (`202 Accepted`).
- `GET /api/v1/payments/{payment_id}` — получение статуса платежа.
- Статический API-ключ для всех endpoint: заголовок `X-API-Key`.
- Idempotency по `Idempotency-Key`: повтор с тем же ключом возвращает `409 Conflict`.
- Outbox pattern: платеж и событие создаются в одной транзакции, публикация в брокер — через relay.
- Consumer:
  - читает `payments.new`,
  - эмулирует обработку `2-5` секунд,
  - обновляет статус (`90% succeeded`, `10% failed`),
  - отправляет webhook с retry.
- Dead Letter Queue: после 3 попыток обработки сообщение уходит в `payments.new.dlq` через `dead-letter-exchange`.

## Технологии

- FastAPI, Pydantic v2
- SQLAlchemy 2.0 (async), asyncpg
- PostgreSQL 16
- RabbitMQ 3 (management UI)
- Alembic
- Docker Compose

## Быстрый старт

1. Подготовка переменных окружения:

```bash
cp .env.example .env
```

2. Запуск окружения:

```bash
make start
```

3. Проверка контейнеров:

```bash
docker compose ps
```

Ожидается 4 сервиса: `postgres`, `rabbitmq`, `api`, `consumer`.

## URL для тестирования

- API docs: `http://localhost:8002/docs`
- RabbitMQ UI: `http://localhost:15672` (`guest/guest`)

## Быстрая ручная проверка (smoke)

```bash
BASE=http://localhost:8002/api/v1
PAYMENTS="$BASE/payments"
KEY=supersecretkey
IDEM=$(uuidgen)
PAYLOAD='{"amount":321.45,"currency":"USD","description":"quick-check","metadata":{"order_id":"ORD-QUICK"},"webhook_url":"https://webhook.site/<your-id>"}'
```

### 1) Auth: без API-ключа -> 401

```bash
curl -i -s -X POST "$PAYMENTS" \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"
```

### 2) Создание и дубликат: 202, затем 409

```bash
curl -s -X POST "$PAYMENTS" \
  -H "X-API-Key: $KEY" \
  -H "Idempotency-Key: $IDEM" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" | jq .

curl -s -X POST "$PAYMENTS" \
  -H "X-API-Key: $KEY" \
  -H "Idempotency-Key: $IDEM" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" | jq .
```

### 3) Статус: сразу pending, через 5-10 сек succeeded/failed

```bash
PID=$(curl -s -X POST "$PAYMENTS" \
  -H "X-API-Key: $KEY" \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" | jq -r .payment_id)

curl -s -H "X-API-Key: $KEY" "$PAYMENTS/$PID" | jq .
sleep 7
curl -s -H "X-API-Key: $KEY" "$PAYMENTS/$PID" | jq .
```

### 4) Валидация/Not Found: 422 и 404

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$PAYMENTS" \
  -H "X-API-Key: $KEY" \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{"amount":100,"currency":"JPY","description":"bad-currency","metadata":{},"webhook_url":"https://webhook.site/<your-id>"}'

curl -s -o /dev/null -w "%{http_code}\n" \
  -H "X-API-Key: $KEY" \
  "$PAYMENTS/00000000-0000-0000-0000-000000000000"
```

## Ручная проверка DLQ

1. Очистить очереди:

```bash
docker compose exec -T rabbitmq rabbitmqctl purge_queue payments.new
docker compose exec -T rabbitmq rabbitmqctl purge_queue payments.new.dlq
```

2. Опубликовать заведомо невалидный для БД `payment_id`:

```bash
docker compose exec -T rabbitmq rabbitmqadmin -u guest -p guest publish \
  exchange=amq.default \
  routing_key=payments.new \
  payload='{"payment_id":"00000000-0000-0000-0000-000000000003"}' \
  payload_encoding=string \
  properties='{"content_type":"application/json"}'
```

3. Проверить, что сообщение ушло в DLQ:

```bash
sleep 2
docker compose exec -T rabbitmq rabbitmqctl list_queues name messages_ready messages_unacknowledged
```

Ожидается: `payments.new.dlq` имеет `Ready >= 1`.

4. Подтвердить 3 попытки обработки в логах consumer:

```bash
docker compose logs --since=2m consumer | rg '00000000-0000-0000-0000-000000000003|PaymentNotFoundError'
```

Ожидается: строка `Received payment event ...` появляется 3 раза, затем ошибка.

## Тесты и линт

```bash
make test
make lint
```

## Команды разработки

- `make start` — запуск docker compose.
- `make test` — запуск `pytest`.
- `make lint` — форматирование + линт (`ruff`).
- `make migrate` — автогенерация миграции Alembic.
