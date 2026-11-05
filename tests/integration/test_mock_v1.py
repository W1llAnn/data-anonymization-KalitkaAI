"""Интеграционные проверки mock-LLM недели 2: сценарии и SSE (пуш 6, Р6)."""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient

from anongw.config import Settings
from anongw.contracts import UpstreamError
from anongw.upstream.client import HttpxUpstreamClient

pytestmark = pytest.mark.integration


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in raw.split("\n\n"):
        if not block.strip():
            continue
        event_name = ""
        data_parts: list[str] = []
        for line in block.split("\n"):
            if line.startswith("event: "):
                event_name = line[len("event: ") :]
            elif line.startswith("data: "):
                data_parts.append(line[len("data: ") :])
        events.append((event_name, json.loads("".join(data_parts))))
    return events


async def test_mock_echo_returns_input_text(mock_llm_url: str) -> None:
    upstream = HttpxUpstreamClient(Settings(model_base_url=mock_llm_url))
    payload = {"model": "mock-echo", "input": "PERSON_1 прислал EMAIL_1"}

    response = await upstream.create_response(payload)

    answer = response["output"][0]["content"][0]["text"]
    assert answer == "PERSON_1 прислал EMAIL_1"


async def test_mock_fail_simulates_model_error(mock_llm_url: str) -> None:
    upstream = HttpxUpstreamClient(Settings(model_base_url=mock_llm_url))
    with pytest.raises(UpstreamError):
        await upstream.create_response({"model": "mock-fail", "input": "текст"})


async def test_mock_stream_sse_events_order_and_deltas(mock_llm_url: str) -> None:
    text = "Персона PERSON_1 пишет письмо"
    async with AsyncClient(timeout=10.0) as http:
        response = await http.post(
            f"{mock_llm_url}/v1/responses",
            json={"model": "mock-echo", "input": text, "stream": True},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(response.text)
    names = [name for name, _ in events]
    assert names[0] == "response.created"
    assert names[-1] == "response.completed"
    assert "response.output_item.added" in names
    assert "response.output_text.done" in names

    deltas = "".join(data["delta"] for name, data in events if name == "response.output_text.delta")
    assert deltas == text

    completed = events[-1][1]
    assert completed["status"] == "completed"
    assert completed["output"][0]["content"][0]["text"] == text


async def test_stream_requests_are_recorded(mock_llm_url: str) -> None:
    async with AsyncClient(timeout=10.0) as http:
        await http.delete(f"{mock_llm_url}/__recorded")
        await http.post(
            f"{mock_llm_url}/v1/responses",
            json={"model": "mock-echo", "input": "текст", "stream": True},
        )
        recorded = (await http.get(f"{mock_llm_url}/__recorded")).json()

    assert len(recorded) == 1
    assert recorded[0]["payload"]["stream"] is True
