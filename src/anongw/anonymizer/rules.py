"""Rule-детекторы: строгие форматы и адреса (недели 2–3, Р2).

Строгие форматы (телефоны, email, ИНН/СНИЛС/паспорт, карты, счета) проверяются
контрольными суммами — «неоднозначные числа» остаются в тексте нетронутыми.
Адреса — канонические записи с сокращениями (г./ул./д./кв.); «рыхлые» адреса
без маркеров — работа модели (неделя 6+). Персоны — словарь в names.py.
"""

from __future__ import annotations

import re

from anongw.anonymizer.names import detect_persons
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
# Карта: 13–19 цифр слитно либо группами по 4 (16/19); валидность — алгоритм Луна.
# ОМС (16 цифр) использует совместимый алгоритм, поэтому при выделении ОМС в
# отдельный тип понадобится контекстное слово.
_CARD_PLAIN_RE = re.compile(r"(?<!\d)\d{13,19}(?!\d)")
_CARD_GROUPED_RE = re.compile(r"(?<!\d)(?:\d{4}[ -]){3}\d{4}(?:[ -]\d{3})?(?!\d)")
# Счёт: 20 цифр сами по себе неоднозначны, детектим только с контекстным словом
_ACCOUNT_RE = re.compile(r"сч[её]т\w*\s*(?:№|N|#)?\s*(\d{20})(?!\d)", re.IGNORECASE)

# Адрес: канонические сегменты с сокращениями; хотя бы город или улица
_CITY_SEG = r"(?:г|гор(?:од)?)\.?\s*[А-ЯЁ][а-яё-]+"
_STREET_SEG = r"(?:ул|улица|пр-т|проспект|пер|переулок|ш|шоссе)\.?\s*[А-ЯЁ][а-яё-]+"
_HOUSE_SEG = r"д(?:ом)?\.?\s*\d+(?:\s*(?:к|корп|стр)\.?\s*\w+)?"
_FLAT_SEG = r"кв(?:артира)?\.?\s*\d+"
_TAIL = rf"(?:\s*,\s*{_HOUSE_SEG})?(?:\s*,\s*{_FLAT_SEG})?"
_ADDRESS_RE = re.compile(rf"{_CITY_SEG}(?:\s*,\s*{_STREET_SEG})?{_TAIL}|{_STREET_SEG}{_TAIL}")


def _digits(value: str) -> list[int]:
    return [int(ch) for ch in value if ch.isdigit()]


def _luhn_valid(digits: list[int]) -> bool:
    total = 0
    for position, digit in enumerate(reversed(digits)):
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


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

    for span in _spans(text, _CARD_PLAIN_RE, EntityType.DOC_ID):
        if _luhn_valid(_digits(span.text)):
            found.append(span)
    for span in _spans(text, _CARD_GROUPED_RE, EntityType.DOC_ID):
        if _luhn_valid(_digits(span.text)):
            found.append(span)
    for match in _ACCOUNT_RE.finditer(text):
        start, end = match.span(1)  # ПДн — только номер, слово «счёт» остаётся в тексте
        found.append(Span(start, end, EntityType.DOC_ID, match.group(1)))

    found += _spans(text, _PHONE_RE, EntityType.PHONE)

    return _resolve_overlaps(found)


def detect(text: str) -> list[Span]:
    """Полный rule-конвейер: строгие форматы + адреса + персоны (словарь).

    Порядок добавления задаёт приоритет при пересечениях (строгие форматы
    сильнее адресов, адреса — сильнее персон). Модель подключается в неделе 6
    и занимает место между адресами и словарём.
    """
    found = detect_strict(text)
    found += _spans(text, _ADDRESS_RE, EntityType.ADDRESS)
    found += detect_persons(text)
    return _resolve_overlaps(found)
