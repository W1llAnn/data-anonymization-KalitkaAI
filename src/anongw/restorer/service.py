"""Обратная подстановка маркеров (каркас недели 1)."""

from __future__ import annotations

import re

from anongw.contracts import MappingStore, Marker

_MARKER_RE = re.compile(r"\b((?:PERSON|PHONE|EMAIL|ADDRESS|DOC_ID)_\d+)\b")


class MappingRestorer:
    """Заменяет известные маркеры исходными значениями из хранилища.

    Неизвестные маркеры (в том числе придуманные моделью) передаются как есть.
    Стриминговая версия с буфером на границах delta — Р5, неделя 6.
    """

    def __init__(self, store: MappingStore) -> None:
        self._store = store

    async def restore(self, text: str, *, user_id: str, context_id: str) -> str:
        parts: list[str] = []
        pos = 0
        for match in _MARKER_RE.finditer(text):
            parts.append(text[pos : match.start()])
            marker: Marker | None = await self._store.get(user_id, context_id, match.group(1))
            parts.append(marker.original_value if marker is not None else match.group(0))
            pos = match.end()
        parts.append(text[pos:])
        return "".join(parts)
