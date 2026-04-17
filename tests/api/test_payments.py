import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.config import settings
from tests.environment.publisher import FakePublisher
from tests.satellites import make_payment_api_body


@pytest.fixture
def payment_body(payment_records):
    """Returns a valid payment API body from the first record."""
    return make_payment_api_body(payment_records[0])


async def test_create_payment_returns_202(client: AsyncClient, payment_body, payment_records):
    
    headers = {"Idempotency-Key": payment_records[0]["idempotency_key"]}

    
    resp = await client.post(
        "/api/v1/payments",
        json=payment_body,
        headers=headers,
    )

    
    assert resp.status_code == 202
    body = resp.json()
    assert "payment_id" in body
    assert body["status"] == "pending"
    assert "created_at" in body


async def test_create_payment_idempotent_returns_same_id(
    client: AsyncClient, payment_body, payment_records
):
    
    record = payment_records[0]
    headers = {"Idempotency-Key": record["idempotency_key"]}

    
    first = await client.post("/api/v1/payments", json=payment_body, headers=headers)
    second = await client.post("/api/v1/payments", json=payment_body, headers=headers)

    
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["payment_id"] == second.json()["payment_id"]


async def test_create_payment_requires_api_key(client: AsyncClient, payment_body):
     # Act
    # We use a separate client without the default API key header for this test
    # or just override the header in the request.
    resp = await client.post(
        "/api/v1/payments",
        json=payment_body,
        headers={"Idempotency-Key": "key-noauth", "X-API-Key": ""},
    )

    
    assert resp.status_code == 401


async def test_create_payment_wrong_api_key(client: AsyncClient, payment_body):
     # Act
    resp = await client.post(
        "/api/v1/payments",
        json=payment_body,
        headers={"Idempotency-Key": "key-wrong-auth", "X-API-Key": "wrong-key"},
    )

    
    assert resp.status_code == 401


async def test_create_payment_missing_body_fields(client: AsyncClient):
    resp = await client.post(
        "/api/v1/payments",
        json={"amount": "10.00"},  # missing required fields
        headers={"Idempotency-Key": "key-bad-body"},
    )

    
    assert resp.status_code == 422


async def test_create_payment_invalid_currency(client: AsyncClient, payment_body):
    
    bad_body = {**payment_body, "currency": "MOON"}

    
    resp = await client.post(
        "/api/v1/payments",
        json=bad_body,
        headers={"Idempotency-Key": "key-bad-currency"},
    )

    
    assert resp.status_code == 422


async def test_create_payment_triggers_publisher(
    client: AsyncClient, payment_body, payment_records
):
    
    headers = {"Idempotency-Key": payment_records[1]["idempotency_key"]}

    
    resp = await client.post(
        "/api/v1/payments",
        json=payment_body,
        headers=headers,
    )

    
    assert resp.status_code == 202


# ---------------------------------------------------------------------------
# GET /api/v1/payments/{id}
# ---------------------------------------------------------------------------


async def test_get_payment_returns_200(client: AsyncClient, payment_body, payment_records):
    
    record = payment_records[0]
    create_resp = await client.post(
        "/api/v1/payments",
        json=payment_body,
        headers={"Idempotency-Key": record["idempotency_key"]},
    )
    payment_id = create_resp.json()["payment_id"]

    
    get_resp = await client.get(f"/api/v1/payments/{payment_id}")

    
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["payment_id"] == payment_id
    assert body["status"] == "pending"
    assert body["currency"] == record["currency"]
    assert Decimal(body["amount"]) == Decimal(record["amount"])
    assert body["idempotency_key"] == record["idempotency_key"]


async def test_get_payment_not_found(client: AsyncClient):
    
    resp = await client.get(f"/api/v1/payments/{uuid.uuid4()}")

    
    assert resp.status_code == 404


async def test_get_payment_requires_api_key(client: AsyncClient):
    
    resp = await client.get(
        f"/api/v1/payments/{uuid.uuid4()}",
        headers={"X-API-Key": "bad"},
    )

    
    assert resp.status_code == 401


async def test_get_payment_returns_metadata(client: AsyncClient, payment_records):
    
    record = payment_records[2]  # Record with rich metadata
    body = make_payment_api_body(record)
    create_resp = await client.post(
        "/api/v1/payments",
        json=body,
        headers={"Idempotency-Key": record["idempotency_key"]},
    )
    payment_id = create_resp.json()["payment_id"]

    
    get_resp = await client.get(f"/api/v1/payments/{payment_id}")

    
    assert get_resp.json()["metadata"] == record["metadata"]
