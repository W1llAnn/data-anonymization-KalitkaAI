"""Движок сборки текста из частей с трекингом границ ПДн."""

from __future__ import annotations

from dataclasses import dataclass

ENTITY_TYPES = frozenset({"PERSON", "PHONE", "EMAIL", "ADDRESS", "DOC_ID"})


@dataclass(frozen=True)
class Slot:
    """Фрагмент текста с персональными данными, вставляемый в шаблон."""

    entity_type: str
    value: str
    entity_id: str  # одинаковый для повторных упоминаний одного лица/объекта


@dataclass(frozen=True)
class EntitySpan:
    """Разметка: полуинтервал [start, end) в символах текста примера."""

    start: int
    end: int
    entity_type: str
    entity_id: str
    text: str


def render_parts(parts: list[str | Slot]) -> tuple[str, list[EntitySpan]]:
    """Склеивает части в текст и фиксирует границы каждого Slot."""
    chunks: list[str] = []
    spans: list[EntitySpan] = []
    pos = 0
    for part in parts:
        value = part.value if isinstance(part, Slot) else part
        if isinstance(part, Slot):
            spans.append(EntitySpan(pos, pos + len(value), part.entity_type, part.entity_id, value))
        chunks.append(value)
        pos += len(value)
    return "".join(chunks), spans
