"""Конвейер запроса: сбор текстов, анонимизация, сборка payload для модели (M1)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from anongw.anonymizer.normalize import normalize_value
from anongw.anonymizer.rules import detect_strict
from anongw.api.schemas import InputFilePart, InputTextPart, MessageItem, ResponsesApiRequest
from anongw.contracts import Anonymizer, FileExtractor
from anongw.files.datauri import parse_data_uri


async def collect_input_texts(request: ResponsesApiRequest, extractor: FileExtractor) -> list[str]:
    """Все тексты запроса (валидация файлов — сразу, до модели)."""
    texts: list[str] = []
    if isinstance(request.input, str):
        texts.append(request.input)
    else:
        for item in request.input:
            texts.extend(await _texts_of_item(item, extractor))
    if request.instructions:
        texts.append(request.instructions)
    return texts


async def collect_normalized_values(
    request: ResponsesApiRequest, extractor: FileExtractor
) -> list[str]:
    """Нормализованные значения ПДн всех текстов — вход resolve_context."""
    values: list[str] = []
    for text in await collect_input_texts(request, extractor):
        for span in detect_strict(text):
            values.append(normalize_value(span.text, span.entity_type))
    return values


async def build_model_payload(
    request: ResponsesApiRequest,
    extractor: FileExtractor,
    anonymizer: Anonymizer,
    *,
    user_id: str,
    context_id: str,
) -> dict[str, Any]:
    """Готовый payload для внешней модели: только маркеры, без исходных текстов.

    input_file превращается в input_text с извлечённым текстом — файл наружу
    не уходит. tools — пока как есть (санитизация — неделя 5).
    """

    async def anon(text: str) -> str:
        return (await anonymizer.anonymize(text, user_id=user_id, context_id=context_id)).text

    payload: dict[str, Any] = {"model": request.model, "store": False}

    if request.instructions:
        payload["instructions"] = await anon(request.instructions)

    if isinstance(request.input, str):
        payload["input"] = await anon(request.input)
    else:
        items: list[dict[str, Any]] = []
        for item in request.input:
            items.append(await _anonymized_item(item, extractor, anon))
        payload["input"] = items

    if request.tools:
        payload["tools"] = [tool.model_dump() for tool in request.tools]
    return payload


def llm_answer_text(llm_response: dict[str, Any]) -> str:
    """Текст ответа внешней модели — первый output_text из message-элементов."""
    for item in llm_response.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") == "output_text":
                return str(part.get("text", ""))
    return ""


async def _texts_of_item(item: MessageItem, extractor: FileExtractor) -> list[str]:
    if isinstance(item.content, str):
        return [item.content]

    texts: list[str] = []
    for part in item.content:
        if isinstance(part, InputTextPart):
            texts.append(part.text)
        elif isinstance(part, InputFilePart):
            uri = parse_data_uri(part.file_data)
            texts.append(await extractor.extract_text(uri.payload_b64, part.filename))
    return texts


async def _anonymized_item(
    item: MessageItem, extractor: FileExtractor, anon: Callable[[str], Awaitable[str]]
) -> dict[str, Any]:
    if isinstance(item.content, str):
        return {"role": item.role, "content": await anon(item.content)}

    parts: list[dict[str, Any]] = []
    for part in item.content:
        if isinstance(part, InputTextPart):
            parts.append({"type": "input_text", "text": await anon(part.text)})
        elif isinstance(part, InputFilePart):
            uri = parse_data_uri(part.file_data)
            text = await extractor.extract_text(uri.payload_b64, part.filename)
            parts.append({"type": "input_text", "text": await anon(text)})
    return {"role": item.role, "content": parts}
