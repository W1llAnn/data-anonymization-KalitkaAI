"""Проверки недели 2, пуш 5 (Р5): resolve_context и сквозная нумерация."""

from __future__ import annotations

import asyncio
from contextlib import suppress

import pytest

from anongw.anonymizer.persistent import PersistentAnonymizer
from anongw.contracts import EntityType, Marker
from anongw.mapping.context import resolve_context
from anongw.mapping.sqlite_store import SqliteMappingStore

pytestmark = pytest.mark.unit


def _store(tmp_path) -> SqliteMappingStore:
    return SqliteMappingStore(str(tmp_path / "m.db"))


async def test_resolve_context_new_when_no_history(tmp_path) -> None:
    store = _store(tmp_path)
    context_id = await resolve_context(store, "u1", ["79162534781"])
    assert context_id  # новый uuid
    assert await resolve_context(store, "u2", ["79162534781"]) != context_id  # изоляция


async def test_resolve_context_continues_existing(tmp_path) -> None:
    store = _store(tmp_path)
    await store.put("u1", "ctx-a", Marker("PERSON_1", EntityType.PERSON, "Иван", "иван"))
    await store.put("u1", "ctx-a", Marker("PHONE_1", EntityType.PHONE, "+7...", "79162534781"))

    context_id = await resolve_context(store, "u1", ["иван", "79162534781"])
    assert context_id == "ctx-a"


async def test_resolve_context_majority_wins(tmp_path) -> None:
    store = _store(tmp_path)
    await store.put("u1", "ctx-a", Marker("PERSON_1", EntityType.PERSON, "И", "ключ1"))
    await store.put("u1", "ctx-a", Marker("PERSON_2", EntityType.PERSON, "П", "ключ2"))
    await store.put("u1", "ctx-b", Marker("PERSON_1", EntityType.PERSON, "А", "ключ3"))

    # два значения из ctx-a против одного из ctx-b
    context_id = await resolve_context(store, "u1", ["ключ1", "ключ2", "ключ3"])
    assert context_id == "ctx-a"


async def test_resolve_context_tie_break_latest(tmp_path) -> None:
    store = _store(tmp_path)
    await store.put("u1", "ctx-old", Marker("PERSON_1", EntityType.PERSON, "И", "общий"))
    await store.put("u1", "ctx-new", Marker("PERSON_1", EntityType.PERSON, "И", "общий"))
    with store._lock:
        store._conn.execute(
            "UPDATE mappings SET created_at = '2030-01-01T00:00:00+00:00' "
            "WHERE context_id = 'ctx-new'"
        )
        store._conn.commit()

    context_id = await resolve_context(store, "u1", ["общий"])
    assert context_id == "ctx-new"


async def test_persistent_numbering_continues_across_requests(tmp_path) -> None:
    store = _store(tmp_path)
    anonymizer = PersistentAnonymizer(store)

    first = await anonymizer.anonymize(
        "Тел. +7 916 253-47-81, почта a@ex.com", user_id="u1", context_id="ctx"
    )
    second = await anonymizer.anonymize(
        "Повтор: 8 (916) 253-47-81 и новый +7 900 111-11-11",
        user_id="u1",
        context_id="ctx",
    )

    assert first.text == "Тел. PHONE_1, почта EMAIL_1"
    # Тот же номер — прежний маркер, новый телефон — следующий номер
    assert second.text == "Повтор: PHONE_1 и новый PHONE_2"


async def test_persistent_numbering_isolated_by_context_and_user(tmp_path) -> None:
    store = _store(tmp_path)
    anonymizer = PersistentAnonymizer(store)

    await anonymizer.anonymize("+7 916 253-47-81", user_id="u1", context_id="ctx-a")
    other_context = await anonymizer.anonymize("+7 916 253-47-81", user_id="u1", context_id="ctx-b")
    other_user = await anonymizer.anonymize("+7 916 253-47-81", user_id="u2", context_id="ctx-a")

    # В каждом контексте нумерация своя: PHONE_1
    assert "PHONE_1" in other_context.text
    assert "PHONE_1" in other_user.text


async def test_markers_available_for_restoration(tmp_path) -> None:
    store = _store(tmp_path)
    anonymizer = PersistentAnonymizer(store)

    result = await anonymizer.anonymize(
        "Итог: счёт 40817000000000000000", user_id="u1", context_id="ctx"
    )
    # Пара пережила запрос — доступна восстановителю
    marker = await store.get("u1", "ctx", "DOC_ID_1")
    assert marker is not None
    assert marker.normalized_value == "40817000000000000000"
    assert result.text == "Итог: счёт DOC_ID_1"


async def test_ttl_loop_cancellable(tmp_path) -> None:
    store = _store(tmp_path)
    from anongw.app import _ttl_cleanup_loop

    task = asyncio.create_task(_ttl_cleanup_loop(store, interval_seconds=3600))
    await asyncio.sleep(0.05)
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    # Хранилище живо, повторный вызов работает
    assert await store.cleanup_expired() == 0
