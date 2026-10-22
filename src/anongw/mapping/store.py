"""Хранилище соответствий в памяти (каркас недели 1)."""

from __future__ import annotations

from anongw.contracts import Marker


class InMemoryMappingStore:
    """Словарь с ключом (user_id, context_id, marker); записи живут до перезапуска.

    SQLite-хранилище с TTL-очисткой — Р5 (недели 1–2 и 4, docs/git-workflow.md §4).
    """

    def __init__(self) -> None:
        self._data: dict[tuple[str, str, str], Marker] = {}

    async def get(self, user_id: str, context_id: str, marker: str) -> Marker | None:
        return self._data.get((user_id, context_id, marker))

    async def put(self, user_id: str, context_id: str, marker: Marker) -> None:
        self._data[(user_id, context_id, marker.marker)] = marker

    async def cleanup_expired(self) -> int:
        """TTL в каркасе нет — удалять нечего."""
        return 0
