"""Маршруты API: health-проверка и точка входа профиля Responses API."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/v1/responses")
async def create_response() -> JSONResponse:
    """Точка профиля Responses API.

    Схемы запроса/ответа — неделя 2 (r1-api-schemas), полный конвейер — неделя 3 (M1).
    Явный 501, чтобы клиент не получил ложный успех.
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
