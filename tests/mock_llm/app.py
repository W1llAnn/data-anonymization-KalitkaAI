"""Заглушка внешней модели для docker compose (каркас недели 1).

Рабочий mock с детерминированными ответами и записью входящих запросов — Р6
(week-01-r6-test-plan, week-02-r6-mock-v1).
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

app = FastAPI(title="mock-llm")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/responses")
async def create_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "resp_mock",
        "object": "response",
        "status": "completed",
        "model": payload.get("model", "mock"),
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "mock"}],
            }
        ],
    }
