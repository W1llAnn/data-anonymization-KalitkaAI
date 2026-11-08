"""SSE-инфраструктура сервиса (неделя 4, пуш 1, Р1)."""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient

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


async def test_005_stream_events_in_order(service_client: AsyncClient) -> None:
    text = "Тел. +7 916 253-47-81"
    response = await service_client.post(
        "/v1/responses", json={"model": "mock-echo", "input": text, "stream": True}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(response.text)
    names = [name for name, _ in events]
    assert names[0] == "response.created"
    assert names[-1] == "response.completed"
    assert "response.output_item.added" in names
    assert "response.output_text.delta" in names
    assert "response.output_text.done" in names


async def test_stream_deltas_contain_markers_not_pii(
    service_client: AsyncClient, mock_llm_url: str
) -> None:
    async with AsyncClient() as http:
        await http.delete(f"{mock_llm_url}/__recorded")

    response = await service_client.post(
        "/v1/responses",
        json={"model": "mock-echo", "input": "Тел. +7 916 253-47-81", "stream": True},
    )
    events = _parse_sse(response.text)

    deltas = "".join(data["delta"] for name, data in events if name == "response.output_text.delta")
    assert deltas == "Тел. PHONE_1"

    async with AsyncClient() as http:
        recorded = (await http.get(f"{mock_llm_url}/__recorded")).json()
    assert "+7 916 253-47-81" not in str(recorded[0]["payload"])


async def test_stream_completed_consistent_with_deltas(service_client: AsyncClient) -> None:
    text = "Персона PERSON_1 пишет"
    response = await service_client.post(
        "/v1/responses", json={"model": "mock-echo", "input": text, "stream": True}
    )
    events = _parse_sse(response.text)

    deltas = "".join(data["delta"] for name, data in events if name == "response.output_text.delta")
    completed = events[-1][1]
    completed_text = completed["output"][0]["content"][0]["text"]
    assert deltas == completed_text == text


async def test_stream_with_restore_not_implemented_yet(service_client: AsyncClient) -> None:
    response = await service_client.post(
        "/v1/responses",
        json={"model": "mock-echo", "input": "текст", "stream": True},
        headers={"x-anongw-restore": "true"},
    )
    assert response.status_code == 501
    assert "неделя 6" in response.json()["error"]["message"]
