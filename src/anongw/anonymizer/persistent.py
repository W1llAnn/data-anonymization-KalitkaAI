"""Анонимизатор строгих форматов со сквозной нумерацией через хранилище (Р5).

Отличие от StrictRulesAnonymizer: маркеры продолжают нумерацию контекста
(PERSON_1 останется PERSON_1 в следующем запросе того же диалога), а пары
«маркер → значение» переживают запрос — на них работает обратная подстановка.
"""

from __future__ import annotations

from anongw.anonymizer.normalize import normalize_value
from anongw.anonymizer.rules import detect
from anongw.contracts import AnonymizationResult, Marker
from anongw.mapping.context import MarkerNumberingStore


class PersistentAnonymizer:
    """Детекторы строгих форматов + хранилище соответствий."""

    def __init__(self, store: MarkerNumberingStore) -> None:
        self._store = store

    async def anonymize(self, text: str, *, user_id: str, context_id: str) -> AnonymizationResult:
        spans = detect(text)
        replacements: list[tuple[int, int, Marker]] = []
        created: dict[str, Marker] = {}

        for span in spans:
            normalized = normalize_value(span.text, span.entity_type)
            marker = await self._store.get_by_value(user_id, context_id, normalized)
            if marker is None:
                number = await self._store.next_marker_number(
                    user_id, context_id, str(span.entity_type.value)
                )
                marker = Marker(
                    marker=f"{span.entity_type.value}_{number}",
                    entity_type=span.entity_type,
                    original_value=span.text,
                    normalized_value=normalized,
                )
                await self._store.put(user_id, context_id, marker)
                created[normalized] = marker
            replacements.append((span.start, span.end, marker))

        result = text
        for start, end, marker in sorted(replacements, reverse=True):
            result = result[:start] + marker.marker + result[end:]

        return AnonymizationResult(result, tuple(created.values()))
