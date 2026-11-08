"""Обратная подстановка в не-stream ответах (неделя 3, пуш 5, Р5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from anongw.anonymizer.persistent import PersistentAnonymizer
from anongw.mapping.sqlite_store import SqliteMappingStore
from anongw.restorer.service import MappingRestorer

pytestmark = pytest.mark.unit


async def test_roundtrip_anonymize_then_restore(tmp_path) -> None:
    store = SqliteMappingStore(str(tmp_path / "m.db"))
    anonymizer = PersistentAnonymizer(store)
    restorer = MappingRestorer(store)

    original = "Тел. +7 916 253-47-81, счёт 40817000000000000000, ivan@example.com"
    result = await anonymizer.anonymize(original, user_id="u1", context_id="ctx")
    restored = await restorer.restore(result.text, user_id="u1", context_id="ctx")

    assert result.text == "Тел. PHONE_1, счёт DOC_ID_1, EMAIL_1"
    assert restored == original


async def test_unknown_marker_not_restored(tmp_path) -> None:
    store = SqliteMappingStore(str(tmp_path / "m.db"))
    restorer = MappingRestorer(store)

    text = "Модель упомянула PERSON_99 и EMAIL_1, которых нет в таблице"
    assert await restorer.restore(text, user_id="u1", context_id="ctx") == text


async def test_restore_isolated_by_user_and_context(tmp_path) -> None:
    store = SqliteMappingStore(str(tmp_path / "m.db"))
    anonymizer = PersistentAnonymizer(store)
    restorer = MappingRestorer(store)

    await anonymizer.anonymize("+7 916 253-47-81", user_id="u1", context_id="ctx")

    # Чужой пользователь и чужой контекст не видят соответствий
    assert await restorer.restore("PHONE_1", user_id="u2", context_id="ctx") == "PHONE_1"
    assert await restorer.restore("PHONE_1", user_id="u1", context_id="другой") == "PHONE_1"
    assert await restorer.restore("PHONE_1", user_id="u1", context_id="ctx") == "+7 916 253-47-81"


async def test_expired_marker_not_restored(tmp_path) -> None:
    store = SqliteMappingStore(str(tmp_path / "m.db"))
    anonymizer = PersistentAnonymizer(store)
    restorer = MappingRestorer(store)

    await anonymizer.anonymize("+7 916 253-47-81", user_id="u1", context_id="ctx")
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    with store._lock:
        store._conn.execute("UPDATE mappings SET expires_at = ?", (past,))
        store._conn.commit()

    assert await restorer.restore("PHONE_1", user_id="u1", context_id="ctx") == "PHONE_1"
