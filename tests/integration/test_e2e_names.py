"""E2E: персоны и адреса в сквозном конвейере (неделя 3, пуш 2, Р2)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _answer(response_json: dict) -> str:
    return response_json["output"][0]["content"][0]["text"]


async def test_person_and_address_anonymized_e2e(
    service_client: AsyncClient, mock_llm_url: str
) -> None:
    async with AsyncClient() as http:
        await http.delete(f"{mock_llm_url}/__recorded")

    body = {
        "model": "mock-echo",
        "input": "Письмо для Ивану Петрову, адрес: г. Тверь, ул. Мира, д. 7",
    }
    response = await service_client.post("/v1/responses", json=body)
    assert response.status_code == 200

    answer = _answer(response.json())
    assert "PERSON_1" in answer
    assert "ADDRESS_1" in answer
    assert "Ивану Петрову" not in answer
    assert "г. Тверь" not in answer

    async with AsyncClient() as http:
        recorded = (await http.get(f"{mock_llm_url}/__recorded")).json()
    sent = str(recorded[0]["payload"])
    assert "Ивану Петрову" not in sent
    assert "Тверь" not in sent


async def test_person_marker_consistent_across_requests(service_client: AsyncClient) -> None:
    first = await service_client.post(
        "/v1/responses",
        json={"model": "mock-echo", "input": "Заявление подал Иван Петров"},
    )
    second = await service_client.post(
        "/v1/responses",
        json={"model": "mock-echo", "input": "Решение отравлено Ивану Петрову повторно"},
    )

    assert "PERSON_1" in _answer(first.json())
    # Другой падеж в новом запросе — тот же маркер (леммы + resolve_context)
    assert "PERSON_1" in _answer(second.json())
