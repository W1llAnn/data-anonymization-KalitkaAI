"""Клиент внешней модели."""

from __future__ import annotations

from typing import Any

import httpx

from anongw.config import Settings
from anongw.contracts import UpstreamError


class HttpxUpstreamClient:
    """Обращается к API внешней модели; ключ модели отделён от ключа сервиса (ТЗ п.7).

    Ошибки сети и статусов оборачиваются в UpstreamError для единообразной
    обработки в API-слое.
    """

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.model_base_url.rstrip("/")
        self._api_key = settings.model_api_key
        self._timeout = httpx.Timeout(120.0)

    async def create_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/v1/responses",
                    json=payload,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise UpstreamError(f"Ошибка внешней модели: {exc}") from exc
        data: dict[str, Any] = response.json()
        return data
