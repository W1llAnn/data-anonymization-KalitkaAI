"""Проверки экспорта примеров в файлы и разделения выборок (пуш 3, Р3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from dataset.generator.export_files import export_example
from docx import Document

pytestmark = pytest.mark.unit


def test_export_txt_roundtrip(tmp_path: Path) -> None:
    path = export_example(tmp_path, "ex_0001", "Тел. +7 900 000-00-00", as_docx=False)
    assert path == tmp_path / "ex_0001.txt"
    assert path.read_text(encoding="utf-8") == "Тел. +7 900 000-00-00"


def test_export_docx_roundtrip(tmp_path: Path) -> None:
    path = export_example(tmp_path, "ex_0002", "Первая строка\nВторая строка", as_docx=True)
    assert path == tmp_path / "ex_0002.docx"

    document = Document(path)
    text = "\n".join(p.text for p in document.paragraphs)
    assert text == "Первая строка\nВторая строка"


def test_files_match_jsonl() -> None:
    """Каждый экспортированный файл соответствует тексту своей записи JSONL."""
    rows = {
        r["id"]: r
        for r in (
            json.loads(line)
            for line in Path("dataset/train/train_w3.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
    }
    files = sorted(Path("dataset/files").glob("ex_*"))
    assert len(files) == 30

    txt_count = sum(1 for f in files if f.suffix == ".txt")
    docx_count = sum(1 for f in files if f.suffix == ".docx")
    assert (txt_count, docx_count) == (21, 9)

    for path in files:
        record = rows[path.stem]
        if path.suffix == ".txt":
            assert path.read_text(encoding="utf-8") == record["text"]
        else:
            # Пустые строки сохраняются пустыми параграфами — сравниваем без фильтра
            document = Document(path)
            assert "\n".join(p.text for p in document.paragraphs) == record["text"]


def test_control_templates_disjoint_from_train() -> None:
    train = {
        r["template"]
        for r in (
            json.loads(line)
            for line in Path("dataset/train/train_w3.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
    }
    control = {
        r["template"]
        for r in (
            json.loads(line)
            for line in Path("dataset/train/control_w3.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
    }
    assert train & control == set()
    assert all(name.startswith("control_") for name in control)
