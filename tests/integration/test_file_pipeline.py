"""Файловые проверки по реестру docs/tests/plan.md (неделя 4, пуш 6, Р6)."""

from __future__ import annotations

import base64
import io

import pytest
from docx import Document
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _docx_with_pii() -> bytes:
    """DOCX с ПДн в параграфе и таблице + метаданные, которые не должны утекать."""
    document = Document()
    document.add_paragraph("Справка выдана Ивану Петрову.")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Телефон"
    table.rows[0].cells[1].text = "+7 916 253-47-81"
    properties = document.core_properties
    properties.author = "Автор Для Проверки"
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _request(filename: str, mime: str, payload: bytes) -> dict:
    return {
        "model": "mock-echo",
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "filename": filename,
                        "file_data": f"data:{mime};base64,{_b64(payload)}",
                    }
                ],
            }
        ],
    }


def _answer(response_json: dict) -> str:
    return response_json["output"][0]["content"][0]["text"]


async def test_024_docx_pipeline_anonymized(service_client: AsyncClient, mock_llm_url: str) -> None:
    async with AsyncClient() as http:
        await http.delete(f"{mock_llm_url}/__recorded")

    response = await service_client.post(
        "/v1/responses", json=_request("cert.docx", "application/octet-stream", _docx_with_pii())
    )
    assert response.status_code == 200

    # Параграф и таблица извлечены, ПДн заменены маркерами
    answer = _answer(response.json())
    assert "PERSON_1" in answer
    assert "PHONE_1" in answer
    assert "Ивану Петрову" not in answer
    assert "+7 916 253-47-81" not in answer


async def test_029_filename_and_metadata_not_leaked(
    service_client: AsyncClient, mock_llm_url: str
) -> None:
    async with AsyncClient() as http:
        await http.delete(f"{mock_llm_url}/__recorded")

    response = await service_client.post(
        "/v1/responses",
        json=_request("секретный_документ.docx", "application/octet-stream", _docx_with_pii()),
    )
    assert response.status_code == 200

    async with AsyncClient() as http:
        recorded = (await http.get(f"{mock_llm_url}/__recorded")).json()
    sent = str(recorded[0]["payload"])
    assert "секретный_документ" not in sent  # имя файла наружу не уходит
    assert "Автор Для Проверки" not in sent  # метаданные не читаются вовсе
    assert "Ивану Петрову" not in sent


async def test_025_cp1251_file_through_pipeline(service_client: AsyncClient) -> None:
    payload = "Тел. +7 900 111-22-33".encode("cp1251")
    response = await service_client.post(
        "/v1/responses", json=_request("note.txt", "text/plain", payload)
    )
    answer = _answer(response.json())
    assert answer == "Тел. PHONE_1"


async def test_025_utf16_file_through_pipeline(service_client: AsyncClient) -> None:
    payload = "Почта: ivan@example.com".encode("utf-16")
    response = await service_client.post(
        "/v1/responses", json=_request("mail.txt", "text/plain", payload)
    )
    answer = _answer(response.json())
    assert answer == "Почта: EMAIL_1"
