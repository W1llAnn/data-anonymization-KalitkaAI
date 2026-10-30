"""Общие фикстуры тестов."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from anongw.app import create_app


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AsyncIterator[AsyncClient]:
    # Тестовая база соответствий — во временном каталоге, репозиторий не загрязняется
    monkeypatch.setenv("ANONGW_MAPPING_DB_PATH", str(tmp_path / "mapping.db"))
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
