"""Smoke-проверка заглушки mock-LLM, которую поднимает docker compose."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from mock_llm.app import app

pytestmark = pytest.mark.unit


async def test_mock_llm_health_and_responses() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://mock") as http:
        health = await http.get("/health")
        response = await http.post("/v1/responses", json={"model": "test", "input": "PERSON_1"})

    assert health.json() == {"status": "ok"}
    assert response.status_code == 200
    assert response.json()["object"] == "response"
