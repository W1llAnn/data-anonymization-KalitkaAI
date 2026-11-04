"""Вывод context_id из нормализованных значений истории (docs/mapping/context-id.md).

Алгоритм: контекст-кандидаты ищутся по значениям; побеждает контекст с максимумом
совпадений, при равенстве — самый свежий по created_at. Нет кандидатов — новый uuid.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from anongw.contracts import Marker


class ContextResolverStore(Protocol):
    """Часть хранилища, нужная для вывода контекста."""

    async def find_contexts_by_values(
        self, user_id: str, normalized_values: list[str]
    ) -> dict[str, int]: ...

    async def latest_created_at(self, user_id: str, context_id: str) -> str | None: ...


class MarkerNumberingStore(Protocol):
    """Часть хранилища, нужная для сквозной нумерации маркеров."""

    async def get_by_value(
        self, user_id: str, context_id: str, normalized_value: str
    ) -> Marker | None: ...

    async def put(self, user_id: str, context_id: str, marker: Marker) -> None: ...

    async def next_marker_number(self, user_id: str, context_id: str, entity_type: str) -> int: ...


async def resolve_context(
    store: ContextResolverStore, user_id: str, normalized_values: list[str]
) -> str:
    candidates = await store.find_contexts_by_values(user_id, normalized_values)
    if not candidates:
        return uuid.uuid4().hex

    best_hits = max(candidates.values())
    finalists = [cid for cid, hits in candidates.items() if hits == best_hits]
    if len(finalists) == 1:
        return finalists[0]

    latest: str | None = None
    winner = finalists[0]
    for context_id in finalists:
        created_at = await store.latest_created_at(user_id, context_id)
        if created_at is not None and (latest is None or created_at > latest):
            latest, winner = created_at, context_id
    return winner
