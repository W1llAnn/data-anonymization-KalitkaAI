"""Контракты межкомпонентных интерфейсов сервиса.

Единый источник правды для всех ролей: доменные типы анонимизации и
Protocol-интерфейсы компонентов. Изменения этого файла — только через ревью Р1
(правила в docs/git-workflow.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol


class EntityType(StrEnum):
    """Типы персональных данных из проверенного профиля (docs/architecture.md §7)."""

    PERSON = "PERSON"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    ADDRESS = "ADDRESS"
    DOC_ID = "DOC_ID"


@dataclass(frozen=True)
class Span:
    """Найденный фрагмент ПДн: полуинтервал [start, end) в символах исходного текста."""

    start: int
    end: int
    entity_type: EntityType
    text: str


@dataclass(frozen=True)
class Marker:
    """Пара «маркер → исходное значение» для таблицы соответствий.

    normalized_value — ключ повторных упоминаний (docs/ml/marker-scheme.md §2):
    одинаковые нормализованные значения получают один маркер внутри контекста.
    """

    marker: str  # PERSON_1, PHONE_2, ...
    entity_type: EntityType
    original_value: str
    normalized_value: str | None = None


@dataclass(frozen=True)
class AnonymizationResult:
    """Результат анонимизации: подготовленный текст и созданные маркеры."""

    text: str
    markers: tuple[Marker, ...]


# --- Ошибки домена ---


class AnongwError(Exception):
    """Базовый класс ошибок сервиса."""


class UnsupportedInputError(AnongwError):
    """Неподдерживаемый ввод: понятная ошибка ДО обращения к модели (ТЗ п.5–6)."""


class UpstreamError(AnongwError):
    """Ошибка обращения к внешней модели."""


# --- Протоколы компонентов ---


class Anonymizer(Protocol):
    """Р2: замена ПДн маркерами; повторные упоминания — одним маркером."""

    async def anonymize(
        self, text: str, *, user_id: str, context_id: str
    ) -> AnonymizationResult: ...


class Restorer(Protocol):
    """Р5: обратная подстановка; неизвестные маркеры не восстанавливаются."""

    async def restore(self, text: str, *, user_id: str, context_id: str) -> str: ...


class MappingStore(Protocol):
    """Р5: хранилище соответствий, изолированное по паре (user_id, context_id)."""

    async def get(self, user_id: str, context_id: str, marker: str) -> Marker | None: ...

    async def put(self, user_id: str, context_id: str, marker: Marker) -> None: ...

    async def cleanup_expired(self) -> int:
        """Удаляет просроченные записи, возвращает количество."""
        ...


class FileExtractor(Protocol):
    """Р4: inline file_data (TXT/DOCX) → текст; метаданные отбрасываются."""

    async def extract_text(self, file_data_b64: str, filename: str | None) -> str: ...


class UpstreamClient(Protocol):
    """Р1: клиент внешней модели; наружу уходят только маркеры.

    payload — подготовленный JSON запроса. Типизированные модели запроса/ответа
    придут в неделе 2 (r1-api-schemas); метод для SSE-стриминга добавится в
    неделе 4 — контракт будет расширен по тем же правилам ревью.
    """

    async def create_response(self, payload: dict[str, Any]) -> dict[str, Any]: ...
