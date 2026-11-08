"""Проверки схем профиля Responses API (неделя 2, пуш 1, Р1)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from anongw.api.schemas import OutputMessage, OutputTextPart, ResponseObject

pytestmark = pytest.mark.unit


async def test_request_with_string_input_passes(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/responses", json={"model": "test-model", "input": "Иван Петров прислал акт"}
    )
    assert response.status_code == 502  # схема принята, дальше — недоступная в unit модель


async def test_request_with_message_array_passes(client: AsyncClient) -> None:
    body = {
        "model": "test-model",
        "instructions": "Помоги разобрать переписку",
        "input": [
            {"role": "user", "content": [{"type": "input_text", "text": "Письмо от Анны"}]},
            {"role": "assistant", "content": "PERSON_1 прислала документ"},
        ],
        "stream": False,
        "store": False,
    }
    response = await client.post("/v1/responses", json=body)
    assert response.status_code == 502


async def test_input_file_with_inline_data_passes(client: AsyncClient) -> None:
    body = {
        "model": "test-model",
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "filename": "letter.txt",
                        "file_data": "data:text/plain;base64,dGVzdCB0ZXh0",
                    }
                ],
            }
        ],
    }
    response = await client.post("/v1/responses", json=body)
    assert response.status_code == 502


async def test_store_true_rejected_with_clear_error(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/responses", json={"model": "m", "input": "текст", "store": True}
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["type"] == "invalid_request_error"
    assert "store" in body["error"]["message"]


async def test_previous_response_id_rejected_as_unsupported(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/responses",
        json={"model": "m", "input": "текст", "previous_response_id": "resp_123"},
    )
    assert response.status_code == 400
    assert "previous_response_id" in response.json()["error"]["message"]


async def test_file_id_rejected_as_unknown_field(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/responses",
        json={
            "model": "m",
            "input": [{"role": "user", "content": [{"type": "input_file", "file_id": "file-abc"}]}],
        },
    )
    assert response.status_code == 400
    message = response.json()["error"]["message"]
    assert "file_id" in message  # поле вне профиля отклонено до модели


def test_response_object_serialization() -> None:
    obj = ResponseObject(
        status="completed",
        model="test-model",
        output=[
            OutputMessage(
                id="msg_1",
                type="message",
                role="assistant",
                status="completed",
                content=[OutputTextPart(type="output_text", text="PERSON_1 прислал документ")],
            )
        ],
    )
    data = obj.model_dump()
    assert data["object"] == "response"
    assert data["output"][0]["content"][0]["text"] == "PERSON_1 прислал документ"
    assert data["id"].startswith("resp_")
