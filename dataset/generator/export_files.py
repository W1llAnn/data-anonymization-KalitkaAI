"""Выгрузка примеров в файлы TXT/DOCX (неделя 3, пуш 3, Р3)."""

from __future__ import annotations

from pathlib import Path


def export_txt(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def export_docx(path: Path, text: str) -> Path:
    from docx import Document  # импорт внутри: зависимость нужна только для DOCX

    path.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    for paragraph in text.split("\n"):
        document.add_paragraph(paragraph)
    document.save(path)
    return path


def export_example(directory: Path, example_id: str, text: str, as_docx: bool) -> Path:
    """Сохраняет пример; DOCX — для каждого третьего файла экспорта (7 txt / 3 docx на 10)."""
    if as_docx:
        return export_docx(directory / f"{example_id}.docx", text)
    return export_txt(directory / f"{example_id}.txt", text)
