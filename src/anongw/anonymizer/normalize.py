"""Нормализация значений для консистентности маркеров (docs/ml/marker-scheme.md §2).

Все пять типов: телефоны/email/документы — преобразования строк; PERSON —
леммы через морфологию (разные падежи → один ключ); ADDRESS — разворот
сокращений и нижний регистр.
"""

from __future__ import annotations

import re

from anongw.anonymizer.names import lemma
from anongw.contracts import EntityType

_NON_DIGITS = re.compile(r"\D+")
_WHITESPACE = re.compile(r"[\s,]+")


def normalize_phone(value: str) -> str:
    """«+7 916 253-47-81» и «8 (916) 253 47 81» → «79162534781»."""
    digits = _NON_DIGITS.sub("", value)
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    return digits


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_doc_id(value: str) -> str:
    """Только цифры: СНИЛС/ИНН/паспорт/карта/счёт нормализуются одинаково."""
    return _NON_DIGITS.sub("", value)


def normalize_person(value: str) -> str:
    """Леммы слов: «Ивану Петрову» и «Иван Петров» → «иван петров»."""
    return " ".join(lemma(word) for word in value.split())


_ABBREVIATIONS = re.compile(
    r"\b(?:квартира|корпус|проспект|переулок|шоссе|город|улица|дом|кв|корп|пр-т|пер|гор|г|ул|д|ш|к)"
    r"\.?(?=[\s,]|$)"
)
_ABBREV_MAP = {
    "квартира": "квартира",
    "кв": "квартира",
    "корпус": "корпус",
    "корп": "корпус",
    "к": "корпус",
    "проспект": "проспект",
    "пр-т": "проспект",
    "переулок": "переулок",
    "пер": "переулок",
    "шоссе": "шоссе",
    "ш": "шоссе",
    "город": "город",
    "гор": "город",
    "г": "город",
    "улица": "улица",
    "ул": "улица",
    "дом": "дом",
    "д": "дом",
}


def normalize_address(value: str) -> str:
    """Разворот сокращений одним проходом и нижний регистр.

    Один проход нужен, чтобы короткие шаблоны («к») не ломали уже развёрнутые
    слова («квартира» → «корпусвартира»).
    """

    def _expand(match: re.Match[str]) -> str:
        return _ABBREV_MAP[match.group(0).rstrip(".").lower()]

    result = _ABBREVIATIONS.sub(_expand, value)
    return _WHITESPACE.sub(" ", result).strip().lower()


def normalize_value(value: str, entity_type: EntityType) -> str:
    """Ключ повторных упоминаний: одинаковые значения → один маркер."""
    match entity_type:
        case EntityType.PHONE:
            return normalize_phone(value)
        case EntityType.EMAIL:
            return normalize_email(value)
        case EntityType.DOC_ID:
            return normalize_doc_id(value)
        case EntityType.PERSON:
            return normalize_person(value)
        case EntityType.ADDRESS:
            return normalize_address(value)
