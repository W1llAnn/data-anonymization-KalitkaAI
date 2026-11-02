"""Единый формат понятных ошибок валидации (неделя 2, пуш 1, Р1)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from anongw.contracts import UnsupportedInputError


def register_error_handlers(app: FastAPI) -> None:
    """Ошибки схемы и неподдерживаемый ввод → 400; ничего не уходит к модели."""

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = "; ".join(
            f"{'.'.join(str(loc) for loc in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": f"Некорректный запрос: {details}",
                    "type": "invalid_request_error",
                }
            },
        )

    @app.exception_handler(UnsupportedInputError)
    async def _unsupported_input_handler(_: Request, exc: UnsupportedInputError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": str(exc),
                    "type": "unsupported_input",
                }
            },
        )
