"""Схемы проверенного профиля Responses API (неделя 2, пуш 1, Р1).

Запрос — что принимаем: model, instructions, input (строка или текстовые
сообщения с inline-файлами), tools (function), stream, store=false.
Всё вне профиля (previous_response_id, file_id/file_url, изображения,
непрозрачные поля) отклоняется на этапе валидации — ДО обращения к модели.
Матрица: docs/architecture.md §5.
"""

from __future__ import annotations

import time
import uuid
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# --- Части входных сообщений ---


class InputTextPart(BaseModel):
    """Текстовая часть сообщения."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["input_text"]
    text: str


class InputFilePart(BaseModel):
    """Inline-файл: только file_data (data URI) и имя для определения формата.

    filename обязателен: по нему определяется формат (docs/files/README.md).
    file_id и file_url в профиле отсутствуют — их передача даст понятную ошибку
    «неизвестное поле».
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["input_file"]
    filename: str
    file_data: str


ContentPart = Annotated[InputTextPart | InputFilePart, Field(discriminator="type")]


class MessageItem(BaseModel):
    """Сообщение истории: только текстовые части."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant", "system", "developer"]
    content: str | list[ContentPart]


class FunctionTool(BaseModel):
    """Определение тестовой функции (цикл function calling — неделя 5)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["function"]
    name: str
    description: str | None = None
    parameters: dict[str, Any] | None = None


class ResponsesApiRequest(BaseModel):
    """Тело POST /v1/responses в пределах проверенного профиля."""

    model_config = ConfigDict(extra="forbid")

    model: str
    instructions: str | None = None
    input: str | list[MessageItem]
    tools: list[FunctionTool] | None = None

    @field_validator("input")
    @classmethod
    def _reject_empty_input(cls, value: str | list[MessageItem]) -> str | list[MessageItem]:
        if isinstance(value, str) and not value.strip():
            raise ValueError("input не должен быть пустой строкой")
        if isinstance(value, list) and not value:
            raise ValueError("input не должен быть пустым списком")
        return value

    stream: bool = False
    store: Literal[False] = False  # store=true отклоняется валидацией


# --- Объект ответа ---


class OutputTextPart(BaseModel):
    type: Literal["output_text"]
    text: str
    annotations: list[Any] = Field(default_factory=list)


class OutputMessage(BaseModel):
    id: str
    type: Literal["message"]
    role: Literal["assistant"]
    status: Literal["in_progress", "completed", "failed"]
    content: list[OutputTextPart]


class FunctionCallItem(BaseModel):
    """Вызов функции в output: id/call_id сохраняются как есть (ТЗ п.6)."""

    id: str
    type: Literal["function_call"]
    call_id: str
    name: str
    arguments: str  # JSON-строка; санитизация содержимого — неделя 5
    status: Literal["in_progress", "completed", "failed"] = "completed"


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


OutputItem = Annotated[OutputMessage | FunctionCallItem, Field(discriminator="type")]


class ResponseObject(BaseModel):
    """Ответ клиенту в совместимой форме."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"resp_{uuid.uuid4().hex[:24]}")
    object: Literal["response"] = "response"
    created_at: int = Field(default_factory=lambda: int(time.time()))
    status: Literal["in_progress", "completed", "failed"]
    model: str
    output: list[OutputItem] = Field(default_factory=list)
    usage: Usage | None = None
