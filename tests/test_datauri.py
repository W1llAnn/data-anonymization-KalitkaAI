"""Проверки разбора data URI и сбора текстов конвейером (пуш 4, Р4)."""

from __future__ import annotations

import base64

import pytest

from anongw.api.pipeline import collect_input_texts
from anongw.api.schemas import ResponsesApiRequest
from anongw.contracts import UnsupportedInputError
from anongw.files.datauri import parse_data_uri
from anongw.files.extractor import TxtDocxFileExtractor

pytestmark = pytest.mark.unit


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def test_data_uri_plain_text_parsed() -> None:
    uri = parse_data_uri(f"data:text/plain;base64,{_b64('Текст письма')}")
    assert uri.mime == "text/plain"
    assert uri.payload_b64 == _b64("Текст письма")


def test_bare_base64_treated_as_text() -> None:
    uri = parse_data_uri(_b64("просто base64"))
    assert uri.mime == "text/plain"


def test_pdf_mime_rejected() -> None:
    with pytest.raises(UnsupportedInputError, match="не поддерживается"):
        parse_data_uri("data:application/pdf;base64,JVBERi0=")


def test_missing_base64_marker_rejected() -> None:
    with pytest.raises(UnsupportedInputError, match="base64"):
        parse_data_uri("data:text/plain,abc")


def test_empty_payload_rejected() -> None:
    with pytest.raises(UnsupportedInputError, match="пустые"):
        parse_data_uri("data:text/plain;base64,")


async def test_collect_texts_string_input() -> None:
    request = ResponsesApiRequest(model="m", input="Иван Петров прислал акт")
    texts = await collect_input_texts(request, TxtDocxFileExtractor())
    assert texts == ["Иван Петров прислал акт"]


async def test_collect_texts_includes_instructions() -> None:
    request = ResponsesApiRequest(model="m", input="текст", instructions="Разбери переписку")
    texts = await collect_input_texts(request, TxtDocxFileExtractor())
    assert texts == ["текст", "Разбери переписку"]


async def test_collect_texts_extracts_file_content() -> None:
    request = ResponsesApiRequest(
        model="m",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Смотрите документ:"},
                    {
                        "type": "input_file",
                        "filename": "letter.txt",
                        "file_data": f"data:text/plain;base64,{_b64('Ивану Петрову выдан акт')}",
                    },
                ],
            }
        ],
    )
    texts = await collect_input_texts(request, TxtDocxFileExtractor())
    assert texts == ["Смотрите документ:", "Ивану Петрову выдан акт"]


async def test_collect_texts_broken_file_fails_before_model() -> None:
    request = ResponsesApiRequest(
        model="m",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "filename": "scan.pdf",
                        "file_data": "data:application/pdf;base64,JVBERi0=",
                    }
                ],
            }
        ],
    )
    with pytest.raises(UnsupportedInputError, match="не поддерживается"):
        await collect_input_texts(request, TxtDocxFileExtractor())
