"""Rule-детекторы строгих форматов (неделя 2, пуш 2, Р2).

Телефоны, email, ИНН/СНИЛС/паспорт. ИНН и СНИЛС проверяются контрольными
суммами — «неоднозначные числа» (номера заказов, даты) не проходят и остаются
в тексте нетронутыми (docs/ml/marker-scheme.md §3, STRICT_RULES).
"""

from __future__ import annotations

import re

from anongw.contracts import EntityType, Span

_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+7|8)"
    r"(?:[-\s(]{0,2}\d{3}[-\s)]{0,2})"
    r"\d{3}[-\s]?\d{2}[-\s]?\d{2}(?!\d)"
)
_EMAIL_RE = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])")
_PASSPORT_RE = re.compile(r"(?<!\d)\d{4}\s\d{6}(?!\d)")
_SNILS_RE = re.compile(r"(?<!\d)\d{3}-\d{3}-\d{3}\s\d{2}(?!\d)")
_INN_10_RE = re.compile(r"(?<!\d)\d{10}(?!\d)")
_INN_12_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")


def _digits(value: str) -> list[int]:
    return [int(ch) for ch in value if ch.isdigit()]


def _inn10_valid(digits: list[int]) -> bool:
    weights = (2, 4, 10, 3, 5, 9, 4, 6, 8)
    control = sum(d * w for d, w in zip(digits[:9], weights, strict=True)) % 11 % 10
    return control == digits[9]


def _inn12_valid(digits: list[int]) -> bool:
    weights1 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    weights2 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    control1 = sum(d * w for d, w in zip(digits[:10], weights1, strict=True)) % 11 % 10
    if control1 != digits[10]:
        return False
    control2 = sum(d * w for d, w in zip(digits[:11], weights2, strict=True)) % 11 % 10
    return control2 == digits[11]


def _snils_valid(digits: list[int]) -> bool:
    control = sum(d * (9 - i) for i, d in enumerate(digits[:9])) % 101
    if control == 100:
        control = 0
    return control == digits[9] * 10 + digits[10]


def _spans(text: str, pattern: re.Pattern[str], entity_type: EntityType) -> list[Span]:
    return [
        Span(match.start(), match.end(), entity_type, match.group(0))
        for match in pattern.finditer(text)
    ]


def _resolve_overlaps(spans: list[Span]) -> list[Span]:
    """Пересекающиеся спаны: остаётся более длинный (email содержит «телефон» и т.п.)."""
    accepted: list[Span] = []
    for span in sorted(spans, key=lambda s: s.start):
        if accepted and span.start < accepted[-1].end:
            previous = accepted[-1]
            if len(span.text) > len(previous.text):
                accepted[-1] = span
            continue
        accepted.append(span)
    return accepted


def detect_strict(text: str) -> list[Span]:
    """Все находки строгих форматов, без пересечений, слева направо."""
    found: list[Span] = []

    found += _spans(text, _EMAIL_RE, EntityType.EMAIL)
    for span in _spans(text, _SNILS_RE, EntityType.DOC_ID):
        if _snils_valid(_digits(span.text)):
            found.append(span)
    found += _spans(text, _PASSPORT_RE, EntityType.DOC_ID)

    for span in _spans(text, _INN_12_RE, EntityType.DOC_ID):
        if _inn12_valid(_digits(span.text)):
            found.append(span)
    for span in _spans(text, _INN_10_RE, EntityType.DOC_ID):
        if _inn10_valid(_digits(span.text)):
            found.append(span)

    found += _spans(text, _PHONE_RE, EntityType.PHONE)

    return _resolve_overlaps(found)
