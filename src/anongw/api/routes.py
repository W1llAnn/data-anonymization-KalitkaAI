"""Маршруты API: health-проверка и конвейер /v1/responses (M1 + SSE)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from anongw.api.pipeline import build_model_payload, collect_normalized_values, llm_answer_text
from anongw.api.schemas import (
    OutputMessage,
    OutputTextPart,
    ResponseObject,
    ResponsesApiRequest,
    Usage,
)
from anongw.mapping.context import resolve_context

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/v1/responses")
async def create_response(body: ResponsesApiRequest, request: Request) -> Response:
    """Сквозной конвейер (M1 + SSE):

    авторизация ключом сервиса → сбор текстов (файлы — до модели) → вывод
    context_id по значениям истории → анонимизация → внешняя модель →
    ответ с маркерами (режим Б — восстановление). При stream=true события
    Responses API ретранслируются потоком.
    """
    state = request.app.state
    settings = state.settings

    authorization = request.headers.get("authorization", "")
    if authorization != f"Bearer {settings.service_api_key}":
        return JSONResponse(
            status_code=401,
            content={"error": {"message": "Неверный ключ сервиса", "type": "authentication_error"}},
        )

    user_id = request.headers.get("x-anongw-user", "default")
    values = await collect_normalized_values(body, state.extractor)
    context_id = await resolve_context(state.mapping_store, user_id, values)
    payload = await build_model_payload(
        body, state.extractor, state.anonymizer, user_id=user_id, context_id=context_id
    )

    # SSE (неделя 4): события Responses API ретранслируются из upstream как есть.
    # Стриминговая обратная подстановка (маркер между delta) — неделя 6.
    if body.stream:
        if request.headers.get("x-anongw-restore", "false").lower() == "true":
            return JSONResponse(
                status_code=501,
                content={
                    "error": {
                        "message": "Обратная подстановка в потоке — неделя 6; "
                        "пока stream доступен только с сохранением маркеров",
                        "type": "not_implemented",
                    }
                },
            )

        async def sse_relay() -> AsyncIterator[str]:
            async for line in state.upstream.stream_response(payload):
                yield line + "\n"

        return StreamingResponse(sse_relay(), media_type="text/event-stream")

    llm_response = await state.upstream.create_response(payload)

    answer = llm_answer_text(llm_response)

    # Два режима (ТЗ п.3): А — маркеры сохраняются (по умолчанию);
    # Б — обратная подстановка исходных значений в текстовые поля ответа.
    # Неизвестные маркеры не восстанавливаются (Restorer передаёт их как есть).
    if request.headers.get("x-anongw-restore", "false").lower() == "true":
        answer = await state.restorer.restore(answer, user_id=user_id, context_id=context_id)

    usage_raw = llm_response.get("usage")
    usage = Usage(**usage_raw) if isinstance(usage_raw, dict) else None
    response = ResponseObject(
        status="completed",
        model=body.model,
        output=[
            OutputMessage(
                id="msg_1",
                type="message",
                role="assistant",
                status="completed",
                content=[OutputTextPart(type="output_text", text=answer)],
            )
        ],
        usage=usage,
    )
    return JSONResponse(response.model_dump())
