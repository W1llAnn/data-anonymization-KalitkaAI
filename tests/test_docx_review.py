"""Ревизия DOCX-конвейера (неделя 4, пуш 4, Р4): порядок, merge, метаданные."""

from __future__ import annotations

import base64
import io
import zipfile

import pytest
from docx import Document

from anongw.contracts import UnsupportedInputError
from anongw.files.extractor import TxtDocxFileExtractor

pytestmark = pytest.mark.unit


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _docx_bytes(build) -> bytes:
    document = Document()
    build(document)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


async def test_document_order_paragraphs_and_tables_preserved() -> None:
    def build(document: Document) -> None:
        document.add_paragraph("Документ для Ивану Петрову")
        table = document.add_table(rows=1, cols=2)
        table.rows[0].cells[0].text = "Телефон"
        table.rows[0].cells[1].text = "+7 900 000-00-00"
        document.add_paragraph("Подпись: Иван Петров")

    text = await TxtDocxFileExtractor().extract_text(_b64(_docx_bytes(build)), "doc.docx")

    lines = text.split("\n")
    assert lines == [
        "Документ для Ивану Петрову",
        "Телефон; +7 900 000-00-00",
        "Подпись: Иван Петров",
    ]


async def test_merged_cells_not_duplicated() -> None:
    def build(document: Document) -> None:
        table = document.add_table(rows=2, cols=3)
        first = table.rows[0].cells
        first[0].text = "Заголовок"
        first[1].merge(first[2])  # объединённая ячейка → дублируется в row.cells
        second = table.rows[1].cells
        second[0].text = "+7 900 111-11-11"
        second[1].text = "ivan@example.com"
        second[2].text = "г. Тверь"

    text = await TxtDocxFileExtractor().extract_text(_b64(_docx_bytes(build)), "t.docx")

    lines = text.split("\n")
    assert lines[0] == "Заголовок"  # не «Заголовок; Заголовок»
    assert lines[1] == "+7 900 111-11-11; ivan@example.com; г. Тверь"


async def test_document_metadata_never_leaks() -> None:
    def build(document: Document) -> None:
        document.add_paragraph("Тело документа")
        properties = document.core_properties
        properties.author = "Секретный Автор"
        properties.comments = "внутренний комментарий"
        properties.title = "служебная записка"

    text = await TxtDocxFileExtractor().extract_text(_b64(_docx_bytes(build)), "m.docx")

    assert text == "Тело документа"
    assert "Секретный" not in text
    assert "служебная" not in text


async def test_renamed_zip_rejected_with_clear_error() -> None:
    # Обычный zip, переименованный в .docx — не документ
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("not-a-doc.txt", "содержимое")
    with pytest.raises(UnsupportedInputError, match="Не удалось прочитать DOCX"):
        await TxtDocxFileExtractor().extract_text(_b64(buffer.getvalue()), "fake.docx")


async def test_multiple_tables_all_extracted() -> None:
    def build(document: Document) -> None:
        for number in (1, 2):
            table = document.add_table(rows=1, cols=1)
            table.rows[0].cells[0].text = f"Таблица {number}"

    text = await TxtDocxFileExtractor().extract_text(_b64(_docx_bytes(build)), "two.docx")
    assert text.split("\n") == ["Таблица 1", "Таблица 2"]
