"""Контрактные проверки профиля по реестру docs/tests/plan.md (пуш 6, Р6).

Имена тестов несут номера реестра; закрытые этой неделей позиции отмечены
в docs/tests/plan.md.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_004_empty_input_rejected_with_clear_error(service_client: AsyncClient) -> None:
    for body in (
        {"model": "m", "input": ""},
        {"model": "m", "input": "   "},
        {"model": "m", "input": []},
    ):
        response = await service_client.post("/v1/responses", json=body)
        assert response.status_code == 400, body
        assert "input" in response.json()["error"]["message"]


async def test_007_response_object_contract(service_client: AsyncClient) -> None:
    response = await service_client.post(
        "/v1/responses", json={"model": "mock-echo", "input": "текст"}
    )
    data = response.json()

    assert response.status_code == 200
    assert data["object"] == "response"
    assert data["id"].startswith("resp_")
    assert isinstance(data["created_at"], int)
    assert data["status"] == "completed"
    assert data["model"] == "mock-echo"

    message = data["output"][0]
    assert message["type"] == "message"
    assert message["role"] == "assistant"
    part = message["content"][0]
    assert part["type"] == "output_text"
    assert isinstance(part["text"], str)

    usage = data["usage"]
    assert isinstance(usage["total_tokens"], int)


async def test_033_malformed_json_rejected(service_client: AsyncClient) -> None:
    response = await service_client.post(
        "/v1/responses",
        content='{"model": "m", "input": ',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["type"] == "invalid_request_error"


async def test_016_repeated_mentions_same_marker(service_client: AsyncClient) -> None:
    response = await service_client.post(
        "/v1/responses",
        json={
            "model": "mock-echo",
            "input": "Тел. +7 916 253-47-81, продублирую: 8 (916) 253-47-81",
        },
    )
    answer = response.json()["output"][0]["content"][0]["text"]
    assert answer.count("PHONE_1") == 2


async def test_035_no_pii_in_service_logs(
    service_client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("DEBUG"):
        await service_client.post(
            "/v1/responses",
            json={"model": "mock-echo", "input": "Тел. +7 916 253-47-81, ivan@example.com"},
        )
    for pii in ("+7 916 253-47-81", "ivan@example.com"):
        assert pii not in caplog.text
