"""Конвейер-эскиз: сбор текстов запроса (неделя 2, пуш 4, Р4).

Собирает все тексты из input (строка, input_text-части, inline-файлы) и
instructions. Файлы разбираются сразу: битые и неподдерживаемые падают понятной
ошибкой ДО обращения к модели. Полный конвейер (анонимизация → модель → ответ)
подключается в неделе 3 (M1).
"""

from __future__ import annotations

from anongw.api.schemas import InputFilePart, InputTextPart, MessageItem, ResponsesApiRequest
from anongw.contracts import FileExtractor
from anongw.files.datauri import parse_data_uri


async def collect_input_texts(request: ResponsesApiRequest, extractor: FileExtractor) -> list[str]:
    texts: list[str] = []

    if isinstance(request.input, str):
        texts.append(request.input)
    else:
        for item in request.input:
            texts.extend(await _texts_of_item(item, extractor))

    if request.instructions:
        texts.append(request.instructions)
    return texts


async def _texts_of_item(item: MessageItem, extractor: FileExtractor) -> list[str]:
    if isinstance(item.content, str):
        return [item.content]

    texts: list[str] = []
    for part in item.content:
        if isinstance(part, InputTextPart):
            texts.append(part.text)
        elif isinstance(part, InputFilePart):
            uri = parse_data_uri(part.file_data)
            text = await extractor.extract_text(uri.payload_b64, part.filename)
            texts.append(text)
    return texts
