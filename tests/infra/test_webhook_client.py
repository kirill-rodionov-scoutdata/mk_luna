from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.config import settings
from app.infra.clients.webhook import WebhookClient


async def test_webhook_client_success(
    payment_records: list[dict[str, Any]], make_mock_http_client: Any
) -> None:
    record = payment_records[0]
    url = record["webhook_url"]
    payload = {"payment_id": str(record["idempotency_key"]), "status": "succeeded"}

    mock_client = make_mock_http_client()

    with patch("httpx.AsyncClient", return_value=mock_client):
        await WebhookClient().send_notification(url, payload)

    mock_client.post.assert_called_once_with(url, json=payload, timeout=10.0)


async def test_webhook_client_sends_correct_payload(
    payment_records: list[dict[str, Any]], make_mock_http_client: Any
) -> None:
    record = payment_records[3]
    url = record["webhook_url"]
    idempotency_key = record["idempotency_key"]
    payload = {
        "payment_id": idempotency_key,
        "status": "pending",
        "idempotency_key": idempotency_key,
    }

    mock_client = make_mock_http_client()

    with patch("httpx.AsyncClient", return_value=mock_client):
        await WebhookClient().send_notification(url, payload)

    _, call_kwargs = mock_client.post.call_args
    assert call_kwargs["json"] == payload
    assert call_kwargs["timeout"] == 10.0


async def test_webhook_client_raises_on_http_error_after_retries(
    payment_records: list[dict[str, Any]], make_mock_http_client: Any
) -> None:
    record = payment_records[1]
    url = record["webhook_url"]
    payload = {"payment_id": record["idempotency_key"]}

    error_response = MagicMock()
    error_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=httpx.Request("POST", url),
            response=httpx.Response(500),
        )
    )
    mock_client = make_mock_http_client(post_return=error_response)

    with patch("asyncio.sleep"):
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.HTTPStatusError):
                await WebhookClient().send_notification(url, payload)

    assert mock_client.post.call_count == settings.webhook.retry_attempts


async def test_webhook_client_raises_on_request_error_after_retries(
    payment_records: list[dict[str, Any]], make_mock_http_client: Any
) -> None:
    record = payment_records[2]
    url = record["webhook_url"]
    payload = {"payment_id": record["idempotency_key"]}

    mock_client = make_mock_http_client(
        post_side_effect=httpx.ConnectError("connection refused")
    )

    with patch("asyncio.sleep"):
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.ConnectError):
                await WebhookClient().send_notification(url, payload)

    assert mock_client.post.call_count == settings.webhook.retry_attempts


async def test_webhook_client_succeeds_on_second_attempt(
    payment_records: list[dict[str, Any]], make_mock_http_client: Any
) -> None:
    record = payment_records[4]
    url = record["webhook_url"]
    payload = {"payment_id": record["idempotency_key"]}

    error_response = MagicMock()
    error_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "503 Service Unavailable",
            request=httpx.Request("POST", url),
            response=httpx.Response(503),
        )
    )
    success_response = MagicMock()
    success_response.raise_for_status = MagicMock()

    mock_client = make_mock_http_client(
        post_side_effect=[error_response, success_response]
    )

    with patch("asyncio.sleep"):
        with patch("httpx.AsyncClient", return_value=mock_client):
            await WebhookClient().send_notification(url, payload)

    assert mock_client.post.call_count == 2
