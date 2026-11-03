"""API-уровень: файлы в input обрабатываются/отклоняются до модели (пуш 4, Р4)."""

from __future__ import annotations

import base64

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.unit


def _file_part(filename: str, mime: str, payload: str) -> dict[str, str]:
    encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    return {
        "type": "input_file",
        "filename": filename,
        "file_data": f"data:{mime};base64,{encoded}",
    }


async def test_txt_file_passes_file_stage(client: AsyncClient) -> None:
    body = {
        "model": "m",
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "документ:"},
                    _file_part("letter.txt", "text/plain", "Иван Петров прислал акт"),
                ],
            }
        ],
    }
    response = await client.post("/v1/responses", json=body)
    # Файл разобран успешно; 501 — конвейер приходит в неделе 3
    assert response.status_code == 501


async def test_pdf_file_rejected_before_model(client: AsyncClient) -> None:
    body = {
        "model": "m",
        "input": [
            {"role": "user", "content": [_file_part("scan.pdf", "application/pdf", "%PDF-1.4")]}
        ],
    }
    response = await client.post("/v1/responses", json=body)
    assert response.status_code == 400
    assert response.json()["error"]["type"] == "unsupported_input"


async def test_broken_base64_rejected(client: AsyncClient) -> None:
    body = {
        "model": "m",
        "input": [
            {"role": "user", "content": [_file_part("x.txt", "text/plain", "текст")]},
        ],
    }
    body["input"][0]["content"][0]["file_data"] = "data:text/plain;base64,%%%битый%%%"
    response = await client.post("/v1/responses", json=body)
    assert response.status_code == 400
    assert "base64" in response.json()["error"]["message"]


async def test_cp1251_txt_inside_data_uri(client: AsyncClient) -> None:
    encoded = base64.b64encode("Тел. +7 900 000-00-00".encode("cp1251")).decode("ascii")
    body = {
        "model": "m",
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "filename": "note.txt",
                        "file_data": f"data:text/plain;base64,{encoded}",
                    }
                ],
            }
        ],
    }
    response = await client.post("/v1/responses", json=body)
    assert response.status_code == 501
