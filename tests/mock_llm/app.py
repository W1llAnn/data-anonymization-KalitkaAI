"""Локальная заглушка внешней модели (каркас недели 1; развивает Р6, пуш 6).

Запоминает все входящие запросы (основа тестов утечек ПДн) и отвечает
детерминированным объектом совместимой формы.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import FastAPI, Request


def create_app() -> FastAPI:
    app = FastAPI(title="mock-llm")
    recorded: list[dict[str, Any]] = []

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/responses")
    async def create_response(request: Request) -> dict[str, Any]:
        payload: dict[str, Any] = await request.json()
        recorded.append(
            {
                "payload": payload,
                # Заголовок авторизации нужен тестам раздельных ключей и утечек
                "authorization": request.headers.get("authorization", ""),
            }
        )
        return {
            "id": f"resp_mock_{uuid.uuid4().hex[:12]}",
            "object": "response",
            "created_at": int(time.time()),
            "status": "completed",
            "model": payload.get("model", "mock-model"),
            "output": [
                {
                    "id": "msg_1",
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [
                        {"type": "output_text", "text": "MOCK: ответ заглушки", "annotations": []}
                    ],
                }
            ],
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        }

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
