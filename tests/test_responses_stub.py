from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.unit


async def test_responses_returns_explicit_not_implemented(client: AsyncClient) -> None:
    """Точка /v1/responses до реализации конвейера отвечает явным 501, а не ложным успехом."""
    response = await client.post("/v1/responses", json={"model": "test", "input": "текст"})
    assert response.status_code == 501
    body = response.json()
    assert body["error"]["type"] == "not_implemented"
    assert body["error"]["message"]
