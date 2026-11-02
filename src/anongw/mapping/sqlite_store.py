"""SQLite-хранилище соответствий (неделя 1, пуш 5, Р5).

Схема — schema.sql, применяется при инициализации. Изоляция по паре
(user_id, context_id), TTL через expires_at (просроченная запись равна
отсутствующей). Синхронный sqlite3 внутри async-методов: операции точечные,
отдельный асинхронный драйвер не заводим (docs/architecture.md §6).
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

from anongw.contracts import EntityType, Marker

_SCHEMA = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")

_COLUMNS = (
    "user_id, context_id, marker, entity_type, original_value, "
    "normalized_value, created_at, expires_at"
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SqliteMappingStore:
    """Реализация контракта MappingStore поверх SQLite."""

    def __init__(self, db_path: str, ttl_hours: int = 24) -> None:
        self._ttl = timedelta(hours=ttl_hours)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    @staticmethod
    def _marker_of(row: sqlite3.Row) -> Marker:
        return Marker(
            marker=row["marker"],
            entity_type=EntityType(row["entity_type"]),
            original_value=row["original_value"],
            normalized_value=row["normalized_value"],
        )

    async def get(self, user_id: str, context_id: str, marker: str) -> Marker | None:
        query = f"SELECT {_COLUMNS} FROM mappings WHERE user_id = ? AND context_id = ? AND marker = ? AND expires_at > ?"  # noqa: E501
        with self._lock:
            row = self._conn.execute(
                query, (user_id, context_id, marker, _utcnow().isoformat())
            ).fetchone()
        return self._marker_of(row) if row is not None else None

    async def put(self, user_id: str, context_id: str, marker: Marker) -> None:
        now = _utcnow()
        with self._lock:
            self._conn.execute(
                f"INSERT OR REPLACE INTO mappings ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    context_id,
                    marker.marker,
                    str(marker.entity_type),
                    marker.original_value,
                    marker.normalized_value,
                    now.isoformat(),
                    (now + self._ttl).isoformat(),
                ),
            )
            self._conn.commit()

    async def get_by_value(
        self, user_id: str, context_id: str, normalized_value: str
    ) -> Marker | None:
        """Маркер по нормализованному значению — для повторных упоминаний (Р2)."""
        query = f"SELECT {_COLUMNS} FROM mappings WHERE user_id = ? AND context_id = ? AND normalized_value = ? AND expires_at > ?"  # noqa: E501
        with self._lock:
            row = self._conn.execute(
                query, (user_id, context_id, normalized_value, _utcnow().isoformat())
            ).fetchone()
        return self._marker_of(row) if row is not None else None

    async def find_contexts_by_values(
        self, user_id: str, normalized_values: list[str]
    ) -> dict[str, int]:
        """Контексты-кандидаты по нормализованным значениям: context_id → число совпадений.

        Вход для алгоритма вывода context_id из истории (docs/mapping/context-id.md).
        """
        if not normalized_values:
            return {}
        placeholders = ",".join("?" for _ in normalized_values)
        query = (
            f"SELECT context_id, COUNT(DISTINCT normalized_value) AS hits "
            f"FROM mappings "
            f"WHERE user_id = ? AND normalized_value IN ({placeholders}) AND expires_at > ? "
            f"GROUP BY context_id"
        )
        params: list[str] = [user_id, *normalized_values, _utcnow().isoformat()]
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return {row["context_id"]: int(row["hits"]) for row in rows}

    async def cleanup_expired(self) -> int:
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM mappings WHERE expires_at <= ?", (_utcnow().isoformat(),)
            )
            self._conn.commit()
            return cursor.rowcount

    def close(self) -> None:
        self._conn.close()
