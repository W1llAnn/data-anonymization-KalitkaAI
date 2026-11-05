"""Интеграционные smoke-проверки недели 1: mock-LLM и upstream-клиент."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from anongw.config import Settings
from anongw.upstream.client import HttpxUpstreamClient

pytestmark = pytest.mark.integration


async def test_mock_llm_health(mock_llm_url: str) -> None:
    async with AsyncClient() as http:
        response = await http.get(f"{mock_llm_url}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_upstream_roundtrip_and_recording(mock_llm_url: str) -> None:
    """Upstream-клиент проходит к mock; mock фиксирует payload и ключ модели."""
    settings = Settings(model_base_url=mock_llm_url, model_api_key="test-model-key")
    upstream = HttpxUpstreamClient(settings)
    payload = {"model": "mock-model", "input": "PERSON_1 прислал документ"}

    response = await upstream.create_response(payload)

    assert response["object"] == "response"
    assert response["status"] == "completed"

    async with AsyncClient() as http:
        await http.delete(f"{mock_llm_url}/__recorded")
        await upstream.create_response(payload)
        recorded = (await http.get(f"{mock_llm_url}/__recorded")).json()

    assert len(recorded) == 1
    assert recorded[0]["payload"] == payload
    assert recorded[0]["authorization"] == "Bearer test-model-key"


async def test_service_health_wired_to_mock(service_client: AsyncClient) -> None:
    """Сервис собирается целиком: SQLite-хранилище + mock в роли внешней модели."""
    response = await service_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
