"""Заглушка анонимизатора недели 1."""

from __future__ import annotations

from anongw.contracts import AnonymizationResult


class PassThroughAnonymizer:
    """Текст проходит без изменений.

    Конвейер детекции ПДн (правила + NER) — Р2, недели 2–3 (docs/training.md).
    """

    async def anonymize(self, text: str, *, user_id: str, context_id: str) -> AnonymizationResult:
        return AnonymizationResult(text=text, markers=())
