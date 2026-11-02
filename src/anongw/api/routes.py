"""Маршруты API: health-проверка и точка входа профиля Responses API."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from anongw.api.schemas import ResponsesApiRequest

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/v1/responses")
async def create_response(body: ResponsesApiRequest) -> JSONResponse:
    """Неделя 2: тело проверено схемой — всё вне профиля получает понятную
    ошибку ДО обращения к модели. Разбор input_file — Р4 (пуш 4), полный
    конвейер (анонимизация → модель → ответ) — неделя 3 (M1), поэтому
    на валидный запрос отвечаем явным 501.
    """
    return JSONResponse(
        status_code=501,
        content={
            "error": {
                "message": "Профиль Responses API в разработке: конвейер — неделя 3 (M1)",
                "type": "not_implemented",
            }
        },
    )
