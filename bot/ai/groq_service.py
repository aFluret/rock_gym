from __future__ import annotations

import asyncio
from typing import Any
import logging

import httpx

LOGGER = logging.getLogger(__name__)


class GroqService:
    def __init__(
        self,
        api_key: str,
        model: str,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.8,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._url = "https://api.groq.com/openai/v1/chat/completions"
        self._fallback_models = ("llama-3.3-70b-versatile", "llama-3.1-8b-instant")
        self._max_retries = max(1, max_retries)
        self._retry_backoff_seconds = max(0.1, retry_backoff_seconds)

    async def _request_completion(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> httpx.Response:
        for attempt in range(self._max_retries):
            try:
                response = await client.post(self._url, json=payload, headers=headers)
                if response.status_code in {429, 500, 502, 503, 504}:
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(self._retry_backoff_seconds * (2**attempt))
                        continue
                return response
            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.NetworkError) as exc:
                if attempt >= self._max_retries - 1:
                    raise
                LOGGER.warning("Groq retry after transient error: %s", exc)
                await asyncio.sleep(self._retry_backoff_seconds * (2**attempt))
        raise RuntimeError("Groq retry attempts exhausted")

    async def generate_reply(self, messages: list[dict[str, str]]) -> str:
        if not self._api_key:
            return "Сейчас AI-режим временно недоступен. Могу сразу помочь с записью на пробную тренировку 📅"

        headers = {"Authorization": f"Bearer {self._api_key}"}
        models_to_try = [self._model] + [model for model in self._fallback_models if model != self._model]

        async with httpx.AsyncClient(timeout=20) as client:
            for model in models_to_try:
                payload: dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.5,
                    "max_tokens": 300,
                }
                response = await self._request_completion(client, payload, headers)
                if response.is_success:
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()

                error_message = response.text
                try:
                    error_message = response.json().get("error", {}).get("message", response.text)
                except Exception:  # noqa: BLE001
                    pass

                is_decommissioned = "decommissioned" in error_message.lower()
                if response.status_code == 400 and is_decommissioned:
                    LOGGER.warning("Groq model '%s' is decommissioned, trying fallback model.", model)
                    continue
                response.raise_for_status()

        return "Сейчас AI-режим временно недоступен. Могу сразу помочь с записью на пробную тренировку 📅"
