"""Анонимизатор строгих форматов (неделя 2, пуш 2, Р2).

Заменяет телефоны, email и номера документов маркерами; повторные упоминания
(по нормализованному значению) получают один маркер в рамках запроса.
Связь с хранилищем соответствий и контекстами — пуш 5 (Р5), неделя 2.
PERSON/ADDRESS — неделя 3.
"""

from __future__ import annotations

from anongw.anonymizer.normalize import normalize_value
from anongw.anonymizer.rules import detect_strict
from anongw.contracts import AnonymizationResult, EntityType, Marker


class StrictRulesAnonymizer:
    """STRICT_RULES-этап гибрида: только форматы с гарантируемой precision."""

    async def anonymize(self, text: str, *, user_id: str, context_id: str) -> AnonymizationResult:
        spans = detect_strict(text)

        counters: dict[EntityType, int] = {}
        by_normalized: dict[str, Marker] = {}
        replacements: list[tuple[int, int, Marker]] = []

        for span in spans:
            normalized = normalize_value(span.text, span.entity_type)
            marker = by_normalized.get(normalized)
            if marker is None:
                counters[span.entity_type] = counters.get(span.entity_type, 0) + 1
                marker = Marker(
                    marker=f"{span.entity_type.value}_{counters[span.entity_type]}",
                    entity_type=span.entity_type,
                    original_value=span.text,
                    normalized_value=normalized,
                )
                by_normalized[normalized] = marker
            replacements.append((span.start, span.end, marker))

        # Замена справа налево, чтобы индексы не сдвигались
        result = text
        for start, end, marker in sorted(replacements, reverse=True):
            result = result[:start] + marker.marker + result[end:]

        markers = tuple(by_normalized.values())
        return AnonymizationResult(result, markers)
