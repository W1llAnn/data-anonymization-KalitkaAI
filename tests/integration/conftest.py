"""Фикстуры интеграционных проверок: локальный mock-LLM на реальном HTTP."""

from __future__ import annotations

import threading
import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import uvicorn
from httpx import ASGITransport, AsyncClient

from anongw.app import create_app
from tests.mock_llm.app import create_app as create_mock_app


@pytest.fixture(scope="session")
def mock_llm_url() -> Iterator[str]:
    """Поднимает mock-LLM на свободном порту в отдельном потоке."""
    config = uvicorn.Config(create_mock_app(), host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 10.0
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    if not server.started:
        raise RuntimeError("mock-LLM не поднялся за 10 секунд")

    socket = server.servers[0].sockets[0]
    port = socket.getsockname()[1]
    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5.0)


@pytest.fixture
async def service_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mock_llm_url: str,
) -> AsyncIterator[AsyncClient]:
    """Клиент сервиса, у которого внешней моделью назначен запущенный mock."""
    monkeypatch.setenv("ANONGW_MAPPING_DB_PATH", str(tmp_path / "mapping.db"))
    monkeypatch.setenv("ANONGW_MODEL_BASE_URL", mock_llm_url)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
