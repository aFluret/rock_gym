from __future__ import annotations

import logging

import httpx

LOGGER = logging.getLogger(__name__)


class CrmClient:
    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url

    async def send_lead(self, payload: dict) -> None:
        if not self._webhook_url:
            return
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(self._webhook_url, json=payload)
                response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("CRM webhook failed: %s", exc)
