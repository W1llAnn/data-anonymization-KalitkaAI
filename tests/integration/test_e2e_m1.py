"""Сквозные проверки M1 (неделя 3, пуш 1): конвейер на mock-LLM end-to-end."""

from __future__ import annotations

import base64

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _answer(response_json: dict) -> str:
    return response_json["output"][0]["content"][0]["text"]


async def test_wrong_service_key_rejected(service_client: AsyncClient) -> None:
    response = await service_client.post(
        "/v1/responses",
        json={"model": "mock-echo", "input": "текст"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["type"] == "authentication_error"


async def test_e2e_string_input_anonymized(service_client: AsyncClient) -> None:
    body = {
        "model": "mock-echo",
        "input": "Иван Петров, тел. +7 916 253-47-81, почта ivan.petrov@example.com",
    }
    response = await service_client.post("/v1/responses", json=body)

    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "response"
    assert data["status"] == "completed"
    assert data["model"] == "mock-echo"

    answer = _answer(data)
    assert "PHONE_1" in answer
    assert "EMAIL_1" in answer
    assert "+7 916 253-47-81" not in answer
    assert "ivan.petrov@example.com" not in answer


async def test_no_pii_leak_to_model(service_client: AsyncClient, mock_llm_url: str) -> None:
    """Требование ТЗ п.9: исходные ПДн отсутствуют в перехваченном запросе к модели."""
    async with AsyncClient() as http:
        await http.delete(f"{mock_llm_url}/__recorded")

    pii_text = "Тел. +7 916 253-47-81, счёт 40817000000000000000, m.volkova@example.com"
    response = await service_client.post(
        "/v1/responses", json={"model": "mock-echo", "input": pii_text}
    )
    assert response.status_code == 200

    async with AsyncClient() as http:
        recorded = (await http.get(f"{mock_llm_url}/__recorded")).json()

    assert len(recorded) == 1
    sent = recorded[0]["payload"]["input"]
    assert "+7 916 253-47-81" not in sent
    assert "40817000000000000000" not in sent
    assert "m.volkova@example.com" not in sent
    assert "PHONE_1" in sent
    assert "DOC_ID_1" in sent
    assert "EMAIL_1" in sent


async def test_instructions_and_array_input_anonymized(
    service_client: AsyncClient, mock_llm_url: str
) -> None:
    async with AsyncClient() as http:
        await http.delete(f"{mock_llm_url}/__recorded")

    body = {
        "model": "mock-echo",
        "instructions": "Разбери письмо для anna@example.com",
        "input": [{"role": "user", "content": [{"type": "input_text", "text": "Письмо"}]}],
    }
    response = await service_client.post("/v1/responses", json=body)
    assert response.status_code == 200

    async with AsyncClient() as http:
        recorded = (await http.get(f"{mock_llm_url}/__recorded")).json()
    payload = recorded[0]["payload"]
    assert "anna@example.com" not in str(payload)
    assert "EMAIL_1" in payload["instructions"]


async def test_inline_file_text_anonymized(service_client: AsyncClient, mock_llm_url: str) -> None:
    async with AsyncClient() as http:
        await http.delete(f"{mock_llm_url}/__recorded")

    file_text = "Контакт: +7 900 111-22-33"
    encoded = base64.b64encode(file_text.encode("utf-8")).decode("ascii")
    body = {
        "model": "mock-echo",
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "filename": "letter.txt",
                        "file_data": f"data:text/plain;base64,{encoded}",
                    }
                ],
            }
        ],
    }
    response = await service_client.post("/v1/responses", json=body)
    assert response.status_code == 200

    async with AsyncClient() as http:
        recorded = (await http.get(f"{mock_llm_url}/__recorded")).json()
    sent = str(recorded[0]["payload"])
    assert "+7 900 111-22-33" not in sent
    assert "filename" not in sent  # имя файла наружу не уходит
    assert "PHONE_1" in sent


async def test_context_continues_between_requests(service_client: AsyncClient) -> None:
    first = await service_client.post(
        "/v1/responses",
        json={"model": "mock-echo", "input": "Тел. +7 916 253-47-81"},
    )
    second = await service_client.post(
        "/v1/responses",
        json={"model": "mock-echo", "input": "Повтор: 8 (916) 253-47-81 и новый +7 900 111-11-11"},
    )

    assert "PHONE_1" in _answer(first.json())
    answer = _answer(second.json())
    # Тот же номер другим написанием — прежний маркер, новый — следующий
    assert answer.count("PHONE_1") >= 1
    assert "PHONE_2" in answer
    assert "8 (916) 253-47-81" not in answer


async def test_users_isolated_by_header(service_client: AsyncClient) -> None:
    body = {"model": "mock-echo", "input": "Тел. +7 916 253-47-81"}
    first = await service_client.post("/v1/responses", json=body, headers={"x-anongw-user": "u1"})
    second = await service_client.post("/v1/responses", json=body, headers={"x-anongw-user": "u2"})

    # У каждого пользователя свой контекст и своя нумерация
    assert "PHONE_1" in _answer(first.json())
    assert "PHONE_1" in _answer(second.json())


async def test_stream_returns_not_implemented(service_client: AsyncClient) -> None:
    response = await service_client.post(
        "/v1/responses", json={"model": "mock-echo", "input": "текст", "stream": True}
    )
    assert response.status_code == 501
    assert response.json()["error"]["type"] == "not_implemented"


async def test_model_error_propagates(service_client: AsyncClient) -> None:
    response = await service_client.post(
        "/v1/responses", json={"model": "mock-fail", "input": "текст"}
    )
    assert response.status_code == 502
    assert response.json()["error"]["type"] == "upstream_error"
