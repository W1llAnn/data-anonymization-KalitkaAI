"""Извлечение текста из inline-файлов (каркас недели 1)."""

from __future__ import annotations

from anongw.config import Settings
from anongw.contracts import UnsupportedInputError


class TxtDocxFileExtractor:
    """Каркас: любой файл отклоняется понятной ошибкой до обращения к модели.

    Извлечение TXT (кодировки) и DOCX (параграфы, таблицы) — Р4, недели 1–4.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def extract_text(self, file_data_b64: str, filename: str | None) -> str:
        raise UnsupportedInputError(
            "Обработка файлов в разработке: TXT — неделя 2, DOCX — неделя 4"
        )
