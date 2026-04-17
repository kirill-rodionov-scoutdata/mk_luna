import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.app_layer.interfaces.clients.webhook import AbstractWebhookClient
from app.config import settings

logger = logging.getLogger(__name__)


class WebhookClient(AbstractWebhookClient):
    @retry(
        stop=stop_after_attempt(settings.webhook_retry_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def send_notification(self, url: str, payload: dict) -> None:
        async with httpx.AsyncClient() as client:
            logger.info("Sending webhook to %s", url)
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
