"""Нормализация значений для консистентности маркеров (docs/ml/marker-scheme.md §2).

Строгие типы (PHONE, EMAIL, DOC_ID) — неделя 2. PERSON и ADDRESS (лемматизация
ФИО, разворот сокращений адресов) — неделя 3.
"""

from __future__ import annotations

import re

from anongw.contracts import EntityType

_NON_DIGITS = re.compile(r"\D+")


def normalize_phone(value: str) -> str:
    """«+7 916 253-47-81» и «8 (916) 253 47 81» → «79162534781»."""
    digits = _NON_DIGITS.sub("", value)
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    return digits


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_doc_id(value: str) -> str:
    """Только цифры: СНИЛС/ИНН/паспорт нормализуются одинаково."""
    return _NON_DIGITS.sub("", value)


def normalize_value(value: str, entity_type: EntityType) -> str:
    """Ключ повторных упоминаний: одинаковые значения → один маркер."""
    match entity_type:
        case EntityType.PHONE:
            return normalize_phone(value)
        case EntityType.EMAIL:
            return normalize_email(value)
        case EntityType.DOC_ID:
            return normalize_doc_id(value)
        case EntityType.PERSON | EntityType.ADDRESS:
            raise NotImplementedError("Нормализация PERSON/ADDRESS — неделя 3 (Р2)")
