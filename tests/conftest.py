"""Общие фикстуры тестов."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from anongw.app import create_app

TEST_SERVICE_KEY = "test-service-key"


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AsyncIterator[AsyncClient]:
    """Клиент сервиса без живой модели: конвейер доходит до upstream → 502.

    Файлы и схема проверяются до модели, поэтому 400-ветки тестируются здесь;
    полные e2e-сценарии — integration-фикстура с mock-LLM. База соответствий —
    во временном каталоге.
    """
    monkeypatch.setenv("ANONGW_MAPPING_DB_PATH", str(tmp_path / "mapping.db"))
    monkeypatch.setenv("ANONGW_MODEL_BASE_URL", "http://127.0.0.1:9")  # порт без сервиса
    monkeypatch.setenv("ANONGW_SERVICE_API_KEY", TEST_SERVICE_KEY)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {TEST_SERVICE_KEY}"},
    ) as http:
        yield http
