"""Ревизия TTL-очистки (неделя 4, пуш 5, Р5): стресс, устойчивость, настройки."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from anongw.config import Settings
from anongw.contracts import EntityType, Marker
from anongw.mapping.sqlite_store import SqliteMappingStore

pytestmark = pytest.mark.unit


async def test_stress_mixed_expired_and_alive(tmp_path) -> None:
    """500 записей в 100 контекстах: чистка удаляет ровно просроченные, живые целы."""
    store = SqliteMappingStore(str(tmp_path / "stress.db"))

    past = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    for context in range(100):
        context_id = f"ctx-{context:03d}"
        for number in range(5):
            marker = Marker(
                f"PHONE_{number + 1}",
                EntityType.PHONE,
                f"+7 900 {number:03d}-{number:02d}-{number:02d}",
                f"7900{number:03d}{number:02d}{number:02d}",
            )
            await store.put("u1", context_id, marker)

    with store._lock:
        # Каждая вторая запись просрочена
        store._conn.execute("UPDATE mappings SET expires_at = ? WHERE id % 2 = 1", (past,))
        store._conn.commit()

    removed = await store.cleanup_expired()

    assert removed == 250
    # Живые читаются, просроченные невидимы
    alive = 0
    for context in range(100):
        found = await store.get("u1", f"ctx-{context:03d}", "PHONE_1")
        if found is not None:
            alive += 1
    assert alive == 50  # PHONE_1 — только в «чётных» контекстах
    assert await store.cleanup_expired() == 0  # повторная чистка ничего не находит


async def test_ttl_loop_survives_store_errors(caplog: pytest.LogCaptureFixture) -> None:
    """Ошибка одной итерации не убивает фоновую задачу (неделя 4, ревизия Р5)."""
    from anongw.app import _ttl_cleanup_loop

    calls = 0

    class FlakyStore:
        async def cleanup_expired(self) -> int:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("имитация сбоя базы")
            return 7

    with caplog.at_level("ERROR"):
        task = asyncio.create_task(_ttl_cleanup_loop(FlakyStore(), interval_seconds=0))  # type: ignore[arg-type]
        await asyncio.sleep(0.15)
        task.cancel()

    assert calls >= 2  # после сбоя цикл продолжил работу
    assert "ошибка итерации" in caplog.text


async def test_ttl_loop_logs_removed_count(tmp_path, caplog: pytest.LogCaptureFixture) -> None:
    import logging

    from anongw.app import _ttl_cleanup_loop

    store = SqliteMappingStore(str(tmp_path / "m.db"))
    await store.put("u1", "c", Marker("PERSON_1", EntityType.PERSON, "Иван", "иван"))
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    with store._lock:
        store._conn.execute("UPDATE mappings SET expires_at = ?", (past,))
        store._conn.commit()

    with caplog.at_level(logging.INFO, logger="anongw.mapping"):
        task = asyncio.create_task(_ttl_cleanup_loop(store, interval_seconds=0))  # type: ignore[arg-type]
        await asyncio.sleep(0.15)
        task.cancel()

    assert "удалено записей — 1" in caplog.text


def test_settings_reject_non_positive_ttl() -> None:
    with pytest.raises(ValidationError):
        Settings(mapping_ttl_hours=0)
    with pytest.raises(ValidationError):
        Settings(cleanup_interval_seconds=-5)
    with pytest.raises(ValidationError):
        Settings(max_file_mb=0)
