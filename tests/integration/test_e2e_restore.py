"""E2E: два режима ответа — маркеры сохраняются / обратная подстановка (Р5)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _answer(response_json: dict) -> str:
    return response_json["output"][0]["content"][0]["text"]


async def test_mode_a_keeps_markers_by_default(service_client: AsyncClient) -> None:
    response = await service_client.post(
        "/v1/responses",
        json={"model": "mock-echo", "input": "Тел. +7 916 253-47-81"},
    )
    answer = _answer(response.json())
    assert answer == "Тел. PHONE_1"


async def test_mode_b_restores_original_values(
    service_client: AsyncClient, mock_llm_url: str
) -> None:
    async with AsyncClient() as http:
        await http.delete(f"{mock_llm_url}/__recorded")

    response = await service_client.post(
        "/v1/responses",
        json={"model": "mock-echo", "input": "Тел. +7 916 253-47-81, почта ivan@example.com"},
        headers={"x-anongw-restore": "true"},
    )

    # Клиент получил исходные значения…
    answer = _answer(response.json())
    assert answer == "Тел. +7 916 253-47-81, почта ivan@example.com"

    # …а модель видела только маркеры
    async with AsyncClient() as http:
        recorded = (await http.get(f"{mock_llm_url}/__recorded")).json()
    sent = str(recorded[0]["payload"])
    assert "+7 916 253-47-81" not in sent
    assert "ivan@example.com" not in sent


async def test_mode_b_keeps_unknown_markers(service_client: AsyncClient) -> None:
    response = await service_client.post(
        "/v1/responses",
        json={"model": "mock-echo", "input": "Клиент упомянул PERSON_99 в переписке"},
        headers={"x-anongw-restore": "true"},
    )
    # Маркера нет в таблице соответствий — передаётся как есть
    assert _answer(response.json()) == "Клиент упомянул PERSON_99 в переписке"


async def test_mode_b_restores_across_requests(service_client: AsyncClient) -> None:
    await service_client.post(
        "/v1/responses", json={"model": "mock-echo", "input": "Тел. +7 916 253-47-81"}
    )
    second = await service_client.post(
        "/v1/responses",
        json={"model": "mock-echo", "input": "Повтор: 8 (916) 253-47-81"},
        headers={"x-anongw-restore": "true"},
    )
    # Новый запрос тем же номером другим написанием — восстановлено исходное
    assert _answer(second.json()) == "Повтор: +7 916 253-47-81"
