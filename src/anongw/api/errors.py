"""Единый формат понятных ошибок (недели 2–3, Р1/Р4).

Любой отказ до модели — 400 с человеческим сообщением: технические тексты
Pydantic (discriminator, literal_error, extra_forbidden) переводятся на
понятный язык по правилам ниже. Матрица: docs/compatibility_matrix.md.
"""

from __future__ import annotations

import re

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from anongw.contracts import UnsupportedInputError, UpstreamError

_PART_TAG_RE = re.compile(r"Input tag '([A-Za-z_0-9]+)'")
_KNOWN_PARTS = frozenset({"input_text", "input_file"})


def _humanize_message(error: dict, loc: tuple) -> str:
    """Техническое сообщение Pydantic → понятное объяснение отказа."""
    message = str(error.get("msg", ""))
    error_type = str(error.get("type", ""))
    field = str(loc[-1]) if loc else ""
    path = [str(item) for item in loc]

    if error_type == "extra_forbidden":
        return f"Поле «{field}» вне проверенного профиля API и отклонено до обращения к модели"

    if "tools" in path and error_type == "literal_error":
        return f"Тип инструмента «{error.get('input')}» не поддерживается: только function"

    tag_match = _PART_TAG_RE.search(message)
    if tag_match and tag_match.group(1) not in _KNOWN_PARTS:
        return (
            f"Тип части «{tag_match.group(1)}» не поддерживается: разрешены input_text и input_file"
        )

    if field == "store" or "Input should be False" in message:
        return (
            "store=true не поддерживается: сервис не хранит состояние "
            "(история диалога передаётся явно в input)"
        )

    return message


def register_error_handlers(app: FastAPI) -> None:
    """Ошибки схемы и неподдерживаемый ввод → 400; модель → 502; ничего не уходит наружу."""

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        parts = []
        for error in exc.errors():
            loc = tuple(error["loc"])
            path = ".".join(str(item) for item in loc)
            parts.append(f"{path}: {_humanize_message(error, loc)}")
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": f"Некорректный запрос: {'; '.join(parts)}",
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

    @app.exception_handler(UpstreamError)
    async def _upstream_handler(_: Request, exc: UpstreamError) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "message": str(exc),
                    "type": "upstream_error",
                }
            },
        )
