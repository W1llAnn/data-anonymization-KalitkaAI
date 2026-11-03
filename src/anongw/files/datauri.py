"""Разбор inline file_data в формате data URI (неделя 2, пуш 4, Р4).

OpenAI-совместимые клиенты присылают file_data как «data:<mime>;base64,<payload>».
Голый base64 без префикса допускаем (трактуем как text/plain) — так удобнее
тестам и локальным вызовам; всё остальное — понятная ошибка ДО модели.
"""

from __future__ import annotations

from dataclasses import dataclass

from anongw.contracts import UnsupportedInputError

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_ALLOWED_MIME_PREFIXES = ("text/",)
_ALLOWED_MIME_EXACT = frozenset({_DOCX_MIME, "application/octet-stream"})


@dataclass(frozen=True)
class DataUri:
    mime: str
    payload_b64: str


def parse_data_uri(file_data: str) -> DataUri:
    if not file_data.startswith("data:"):
        return DataUri("text/plain", file_data)

    header, separator, payload = file_data.partition(",")
    if not separator:
        raise UnsupportedInputError("file_data: data URI без данных после запятой")
    if "base64" not in header:
        raise UnsupportedInputError("file_data: поддерживается только base64-кодирование")
    if not payload:
        raise UnsupportedInputError("file_data: пустые данные файла")

    mime = header[len("data:") :].split(";", maxsplit=1)[0].strip().lower()
    if not mime:
        raise UnsupportedInputError("file_data: data URI без типа содержимого")
    allowed = mime.startswith(_ALLOWED_MIME_PREFIXES) or mime in _ALLOWED_MIME_EXACT
    if not allowed:
        raise UnsupportedInputError(
            f"file_data: тип «{mime}» не поддерживается — разрешены TXT и DOCX"
        )
    return DataUri(mime, payload)
