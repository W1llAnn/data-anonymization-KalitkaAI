"""Извлечение текста из TXT/DOCX (прототип недели 1, пуш 4).

Наружу отдаётся только текст: имя файла, метаданные и встроенные объекты
не возвращаются и не пересылаются внешней модели (ТЗ п.2).
Поддерживаемые части DOCX и ограничения — docs/files/README.md.
"""

from __future__ import annotations

import base64
import binascii
import io
from typing import Any

from anongw.config import Settings
from anongw.contracts import UnsupportedInputError

_ALLOWED_EXTENSIONS = frozenset({".txt", ".docx"})


def _validate_filename(filename: str | None) -> str:
    """Возвращает расширение; неподдерживаемое — отказ ДО обращения к модели."""
    if filename is None or not filename.strip():
        raise UnsupportedInputError("Имя файла обязательно: по нему определяется формат")
    name = filename.strip()
    if "/" in name or "\\" in name:
        raise UnsupportedInputError("Имя файла не должно содержать путь")
    dot = name.rfind(".")
    ext = name[dot:].lower() if dot != -1 else ""
    if ext not in _ALLOWED_EXTENSIONS:
        shown = ext if ext else "без расширения"
        raise UnsupportedInputError(
            f"Формат «{shown}» не поддерживается: разрешены только TXT и DOCX"
        )
    return ext


def _decode_txt(data: bytes) -> str:
    """TXT: UTF-8 (с BOM и без), UTF-16 LE/BE по BOM, запасной вариант CP1251."""
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1251")


def _extract_docx(data: bytes) -> str:
    """DOCX: параграфы и таблицы в порядке следования; метаданные не читаем вовсе.

    Формат таблиц (согласован, docs/files/README.md): строка таблицы →
    «ячейка; ячейка», объединённые ячейки не дублируются (python-docx
    возвращает одну и ту же ячейку в row.cells несколько раз).
    """
    from docx import Document
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    try:
        document = Document(io.BytesIO(data))
        parts: list[str] = []
        body = document.element.body
        for child in body.iterchildren():  # порядок документа сохраняется
            if child.tag == qn("w:p"):
                paragraph = Paragraph(child, document)
                if paragraph.text.strip():
                    parts.append(paragraph.text)
            elif child.tag == qn("w:tbl"):
                table = Table(child, document)
                parts.extend(_table_rows(table))
    except Exception as exc:  # повреждённые/не-DOCX файлы дают разные исключения библиотеки
        raise UnsupportedInputError(f"Не удалось прочитать DOCX: {exc}") from exc
    return "\n".join(parts).strip()


def _table_rows(table: Any) -> list[str]:
    """Строки таблицы: непустые ячейки через «; », дубли объединённых схлопываются."""
    rows: list[str] = []
    for row in table.rows:
        cells: list[str] = []
        for cell in row.cells:
            text = cell.text.strip()
            if not cells or cells[-1] != text:  # merge дублирует ячейку в row.cells
                cells.append(text)
        cells = [cell for cell in cells if cell]  # пустые ячейки не сериализуем
        if cells:
            rows.append("; ".join(cells))
    return rows


class TxtDocxFileExtractor:
    """Разбирает inline file_data: base64 → байты → текст нужного формата."""

    def __init__(self, settings: Settings | None = None) -> None:
        max_mb = settings.max_file_mb if settings is not None else 10
        self._max_bytes = max_mb * 1024 * 1024

    async def extract_text(self, file_data_b64: str, filename: str | None) -> str:
        try:
            data = base64.b64decode(file_data_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise UnsupportedInputError("file_data не является корректным base64") from exc

        if len(data) > self._max_bytes:
            limit_mb = self._max_bytes // (1024 * 1024)
            raise UnsupportedInputError(f"Файл больше ограничения {limit_mb} МБ")

        ext = _validate_filename(filename)
        if ext == ".txt":
            return _decode_txt(data)

        text = _extract_docx(data)
        if not text:
            raise UnsupportedInputError("Не удалось извлечь текст из документа")
        return text
