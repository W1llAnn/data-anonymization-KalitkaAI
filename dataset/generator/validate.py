"""Валидатор JSONL-разметки датасета.

Запуск: python -m dataset.generator.validate dataset/train/train_w2.jsonl
Проверяет: уникальность id, границы спанов, совпадение текста спана,
один entity_id → один тип, отсутствие пересечений спанов.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dataset.generator.render import ENTITY_TYPES


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()

    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        where = f"{path.name}:{line_no}"
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{where}: некорректный JSON ({exc})")
            continue

        example_id = record.get("id")
        if example_id in seen_ids:
            errors.append(f"{where}: повтор id {example_id}")
        seen_ids.add(example_id)

        # entity_id уникален в пределах примера, а не всего файла
        entity_types: dict[str, str] = {}
        text = record.get("text", "")
        spans = record.get("entities", [])
        previous_end = -1
        for span in spans:
            start, end = span["start"], span["end"]
            entity_id = span["entity_id"]
            entity_type = span["entity_type"]
            if not 0 <= start < end <= len(text):
                errors.append(f"{where}: спан вне границ текста {entity_id}")
            elif text[start:end] != span["text"]:
                errors.append(f"{where}: текст спана {entity_id} не совпадает с фрагментом")
            if entity_type not in ENTITY_TYPES:
                errors.append(f"{where}: неизвестный тип {entity_type}")
            known = entity_types.setdefault(entity_id, entity_type)
            if known != entity_type:
                errors.append(
                    f"{where}: entity_id {entity_id} имеет два типа ({known}/{entity_type})"
                )
            if start < previous_end:
                errors.append(f"{where}: спаны пересекаются ({entity_id})")
            previous_end = end

    return errors


def main() -> None:
    if len(sys.argv) != 2:
        print("Использование: python -m dataset.generator.validate <файл.jsonl>")
        raise SystemExit(2)
    errors = validate_file(Path(sys.argv[1]))
    for error in errors:
        print(f"ОШИБКА: {error}")
    if errors:
        raise SystemExit(1)
    print("Разметка валидна")


if __name__ == "__main__":
    main()
