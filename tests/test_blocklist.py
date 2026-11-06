"""Блок-лист: всё неподдерживаемое отклоняется понятно и до модели (пуш 4, Р4)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.unit


def _error_message(response_json: dict) -> str:
    return response_json["error"]["message"]


async def test_input_image_part_rejected_with_clear_message(client: AsyncClient) -> None:
    body = {
        "model": "m",
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "фото"},
                    {"type": "input_image", "image_url": "https://example.com/x.png"},
                ],
            }
        ],
    }
    response = await client.post("/v1/responses", json=body)
    assert response.status_code == 400
    message = _error_message(response.json())
    assert "input_image" in message
    assert "не поддерживается" in message


async def test_unknown_content_part_type_rejected(client: AsyncClient) -> None:
    body = {
        "model": "m",
        "input": [{"role": "user", "content": [{"type": "voice_recording", "data": "..."}]}],
    }
    response = await client.post("/v1/responses", json=body)
    assert response.status_code == 400
    assert "не поддерживается" in _error_message(response.json())


async def test_web_search_tool_rejected(client: AsyncClient) -> None:
    body = {
        "model": "m",
        "input": "текст",
        "tools": [{"type": "web_search"}, {"type": "function", "name": "noop"}],
    }
    response = await client.post("/v1/responses", json=body)
    assert response.status_code == 400
    message = _error_message(response.json())
    assert "web_search" in message
    assert "function" in message


async def test_store_true_message_explains_reason(client: AsyncClient) -> None:
    response = await client.post("/v1/responses", json={"model": "m", "input": "т", "store": True})
    message = _error_message(response.json())
    assert "store" in message
    assert "не хранит состояние" in message


async def test_out_of_profile_fields_rejected(client: AsyncClient) -> None:
    for field, value in [
        ("previous_response_id", "resp_1"),
        ("conversation", "conv_1"),
        ("background", True),
        ("metadata", {"a": 1}),
    ]:
        body: dict = {"model": "m", "input": "текст"}
        body[field] = value
        response = await client.post("/v1/responses", json=body)
        assert response.status_code == 400, field
        assert field in _error_message(response.json())
        assert "вне проверенного профиля" in _error_message(response.json())


async def test_file_url_in_part_rejected(client: AsyncClient) -> None:
    body = {
        "model": "m",
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_file", "filename": "x.txt", "file_url": "https://e.com/x"}
                ],
            }
        ],
    }
    response = await client.post("/v1/responses", json=body)
    assert response.status_code == 400
    assert "вне проверенного профиля" in _error_message(response.json())


async def test_image_mime_in_data_uri_rejected_before_model(client: AsyncClient) -> None:
    encoded = "aGVsbG8="
    body = {
        "model": "m",
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "filename": "photo.png",
                        "file_data": f"data:image/png;base64,{encoded}",
                    }
                ],
            }
        ],
    }
    response = await client.post("/v1/responses", json=body)
    assert response.status_code == 400
    assert response.json()["error"]["type"] == "unsupported_input"
    assert "не поддерживается" in _error_message(response.json())
