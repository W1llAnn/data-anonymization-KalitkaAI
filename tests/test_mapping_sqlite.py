"""Проверки SQLite-хранилища соответствий (пуш 5, Р5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from anongw.contracts import EntityType, Marker
from anongw.mapping.sqlite_store import SqliteMappingStore

pytestmark = pytest.mark.unit


def _marker(marker_id: str, value: str, normalized: str) -> Marker:
    return Marker(marker_id, EntityType.PERSON, value, normalized)


async def test_put_get_roundtrip(tmp_path) -> None:
    store = SqliteMappingStore(str(tmp_path / "m.db"))
    await store.put("u1", "c1", _marker("PERSON_1", "Иван Петров", "иван петров"))

    found = await store.get("u1", "c1", "PERSON_1")
    assert found is not None
    assert found.original_value == "Иван Петров"
    assert found.normalized_value == "иван петров"


async def test_isolation_by_user_and_context(tmp_path) -> None:
    store = SqliteMappingStore(str(tmp_path / "m.db"))
    await store.put("u1", "c1", _marker("PERSON_1", "Иван", "иван"))

    assert await store.get("u2", "c1", "PERSON_1") is None
    assert await store.get("u1", "c2", "PERSON_1") is None


async def test_expired_record_is_invisible_and_cleanup_deletes(tmp_path) -> None:
    store = SqliteMappingStore(str(tmp_path / "m.db"))
    await store.put("u1", "c1", _marker("PERSON_1", "Иван", "иван"))

    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    with store._lock:
        store._conn.execute("UPDATE mappings SET expires_at = ?", (past,))
        store._conn.commit()

    assert await store.get("u1", "c1", "PERSON_1") is None
    assert await store.cleanup_expired() == 1
    assert await store.cleanup_expired() == 0


async def test_get_by_value_for_repeated_mentions(tmp_path) -> None:
    store = SqliteMappingStore(str(tmp_path / "m.db"))
    await store.put("u1", "c1", _marker("PERSON_1", "Ивану Петрову", "иван петров"))

    found = await store.get_by_value("u1", "c1", "иван петров")
    assert found is not None
    assert found.marker == "PERSON_1"


async def test_find_contexts_by_values(tmp_path) -> None:
    store = SqliteMappingStore(str(tmp_path / "m.db"))
    await store.put("u1", "ctx-a", _marker("PERSON_1", "Иван", "иван петров"))
    await store.put("u1", "ctx-a", _marker("PHONE_1", "+7 900 000-00-00", "79000000000"))
    await store.put("u1", "ctx-b", _marker("PERSON_1", "Анна", "анна смирнова"))

    found = await store.find_contexts_by_values("u1", ["иван петров", "79000000000"])
    assert found == {"ctx-a": 2}

    only_b = await store.find_contexts_by_values("u1", ["анна смирнова"])
    assert only_b == {"ctx-b": 1}

    assert await store.find_contexts_by_values("u1", []) == {}
    # Изоляция пользователей: у u2 своих контекстов нет
    assert await store.find_contexts_by_values("u2", ["иван петров"]) == {}
