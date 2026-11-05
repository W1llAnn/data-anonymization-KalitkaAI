"""Локальная заглушка внешней модели (неделя 2, пуш 6, Р6).

Сценарии по полю model:
  mock-model (по умолчанию) — фиксированный ответ;
  mock-echo                — отвечает присланным текстом (маркеры проходят насквозь);
  mock-fail                — HTTP 500, симуляция отказа модели (для недель 4–5).

При «stream»: true отдаёт SSE-поток событий Responses API; текст режется на
куски по 10 символов — маркер может оказаться разделённым между delta (заготовка
тестов стриминговой подстановки, недели 6–7).

Все входящие запросы (payload + заголовок авторизации) пишутся в /__recorded —
основа тестов утечек ПДн и раздельных ключей.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterator
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

_CHUNK_SIZE = 10


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _extract_input_text(payload: dict[str, Any]) -> str:
    value = payload.get("input", "")
    if isinstance(value, str):
        return value
    for item in value:
        content = item.get("content", "")
        if isinstance(content, str):
            return content
        for part in content:
            if part.get("type") in {"input_text", "output_text"}:
                return part.get("text", "")
    return ""


def _message_item(answer: str) -> dict[str, Any]:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": answer, "annotations": []}],
    }


def create_app() -> FastAPI:
    app = FastAPI(title="mock-llm")
    recorded: list[dict[str, Any]] = []

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/responses")
    async def create_response(request: Request) -> Response:
        payload: dict[str, Any] = await request.json()
        recorded.append(
            {
                "payload": payload,
                "authorization": request.headers.get("authorization", ""),
            }
        )

        model = payload.get("model", "mock-model")
        if model == "mock-fail":
            return JSONResponse(
                status_code=500,
                content={
                    "error": {"message": "MOCK: симуляция отказа модели", "type": "server_error"}
                },
            )

        input_text = _extract_input_text(payload)
        answer = input_text if model == "mock-echo" else "MOCK: ответ заглушки"
        response_id = f"resp_mock_{uuid.uuid4().hex[:12]}"
        created_at = int(time.time())

        if payload.get("stream") is True:
            return StreamingResponse(
                _event_stream(response_id, created_at, model, answer),
                media_type="text/event-stream",
            )

        return {
            "id": response_id,
            "object": "response",
            "created_at": created_at,
            "status": "completed",
            "model": model,
            "output": [_message_item(answer)],
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        }

    def _event_stream(response_id: str, created_at: int, model: str, answer: str) -> Iterator[str]:
        base = {
            "id": response_id,
            "object": "response",
            "created_at": created_at,
            "model": model,
        }
        item = _message_item(answer)
        yield _sse("response.created", {**base, "status": "in_progress", "output": []})
        yield _sse(
            "response.output_item.added",
            {"type": "response.output_item.added", "output_index": 0, "item": item},
        )
        for position in range(0, len(answer), _CHUNK_SIZE):
            chunk = answer[position : position + _CHUNK_SIZE]
            yield _sse(
                "response.output_text.delta",
                {"type": "response.output_text.delta", "output_index": 0, "delta": chunk},
            )
        yield _sse(
            "response.output_text.done",
            {"type": "response.output_text.done", "output_index": 0, "text": answer},
        )
        yield _sse(
            "response.completed",
            {
                **base,
                "status": "completed",
                "output": [item],
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            },
        )

    @app.get("/__recorded")
    async def get_recorded() -> list[dict[str, Any]]:
        return recorded

    @app.delete("/__recorded")
    async def clear_recorded() -> dict[str, int]:
        count = len(recorded)
        recorded.clear()
        return {"cleared": count}

    return app


app = create_app()
