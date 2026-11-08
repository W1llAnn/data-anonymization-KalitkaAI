from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.unit


async def test_valid_request_reaches_upstream_stage(client: AsyncClient) -> None:
    """Схема и конвейер пройдены: без живой модели — явный 502, а не ложный успех."""
    response = await client.post("/v1/responses", json={"model": "test", "input": "текст"})
    assert response.status_code == 502
    body = response.json()
    assert body["error"]["type"] == "upstream_error"
    assert body["error"]["message"]
