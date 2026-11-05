"""Маршруты API: health-проверка и точка входа профиля Responses API."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from anongw.api.pipeline import collect_input_texts
from anongw.api.schemas import ResponsesApiRequest

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/v1/responses")
async def create_response(body: ResponsesApiRequest, request: Request) -> JSONResponse:
    """Неделя 2: тело проверено схемой, файлы input_file разобраны сразу —
    битые и неподдерживаемые падают понятной ошибкой ДО обращения к модели.
    Полный конвейер (анонимизация → модель → ответ) — неделя 3 (M1), поэтому
    на валидный запрос отвечаем явным 501.
    """
    await collect_input_texts(body, request.app.state.extractor)
    return JSONResponse(
        status_code=501,
        content={
            "error": {
                "message": "Профиль Responses API в разработке: конвейер — неделя 3 (M1)",
                "type": "not_implemented",
            }
        },
    )
