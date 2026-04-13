from __future__ import annotations

from bot.integrations.crm_client import CrmClient


class IntegrationService:
    def __init__(self, crm_webhook_url: str) -> None:
        self._crm_client = CrmClient(crm_webhook_url)

    async def on_booking_created(self, payload: dict) -> None:
        await self._crm_client.send_lead({"event": "booking_created", **payload})

    async def on_booking_contacted(self, payload: dict) -> None:
        await self._crm_client.send_lead({"event": "booking_contacted", **payload})
