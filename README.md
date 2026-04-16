# Payments Service

Async payment processing microservice built with FastAPI, Clean Architecture, RabbitMQ, and PostgreSQL.

## Stack

- **FastAPI** 0.115+ · **Pydantic v2** · **SQLAlchemy 2.0 async** · **asyncpg**
- **Alembic** (async migrations) · **FastStream** (RabbitMQ) · **dependency-injector**
- **PostgreSQL 16** · **RabbitMQ 3** · **Docker + docker-compose**

## Quick Start

```bash
# 1. Copy env file and adjust values if needed
cp .env.example .env

# 2. Start all services
docker-compose up --build

# 3. Run migrations (first time only)
docker-compose exec api alembic upgrade head
```

## API

Interactive docs: http://localhost:8000/docs

All endpoints require the `X-API-Key` header.

### Create payment
```
POST /api/v1/payments
X-API-Key: <key>
Idempotency-Key: <uuid>

{
  "amount": "99.99",
  "currency": "USD",
  "description": "Order #42",
  "metadata": {},
  "webhook_url": "https://example.com/webhook"
}
```

### Get payment
```
GET /api/v1/payments/{payment_id}
X-API-Key: <key>
```

## Architecture

```
domain/          ← Pure Pydantic models, no I/O
app_layer/       ← Use-case services + abstract interfaces
infra/           ← SQLAlchemy, RabbitMQ implementations
api/             ← FastAPI routers, schemas, auth
```

## Local Development (without Docker)

```bash
# Install uv
pip install uv

# Create venv and install deps
uv venv && uv pip install -e ".[dev]"

# Run API
PYTHONPATH=src uvicorn app.main:app --reload

# Run consumer
PYTHONPATH=src python -m app.infra.messaging.consumer
```

## Running Tests

```bash
pytest
```
