"""Проверки rule-детекторов строгих форматов (неделя 2, пуш 2, Р2)."""

from __future__ import annotations

import pytest

from anongw.anonymizer.normalize import normalize_phone
from anongw.anonymizer.rules import detect_strict
from anongw.anonymizer.strict import StrictRulesAnonymizer
from anongw.contracts import EntityType

pytestmark = pytest.mark.unit


def _types(text: str) -> list[EntityType]:
    return [span.entity_type for span in detect_strict(text)]


def test_phone_formats_detected() -> None:
    text = "Тел.: +7 916 253-47-81 или 8(495)123-45-67, пишите на +79162534781"
    assert _types(text) == [EntityType.PHONE] * 3


def test_email_detected() -> None:
    assert _types("Почта: Ivan.Petrov@Example.COM") == [EntityType.EMAIL]


def test_inn_valid_and_invalid() -> None:
    text = "ИНН 7830002293 и 7830002294"
    spans = [s for s in detect_strict(text) if s.entity_type == EntityType.DOC_ID]
    # Контрольная сумма отсекает второе число
    assert len(spans) == 1
    assert spans[0].text == "7830002293"


def test_order_number_not_touched() -> None:
    # «Полезные числа» без валидной контрольной суммы остаются в тексте
    assert detect_strict("Номер заказа 1234567890 от 12.10.2026") == []


def test_snils_valid_and_invalid() -> None:
    spans = [s for s in detect_strict("СНИЛС 112-233-445 95 и 112-233-445 96") if s.text]
    valid = [s for s in spans if s.entity_type == EntityType.DOC_ID]
    assert len(valid) == 1
    assert valid[0].text == "112-233-445 95"


def test_passport_format_detected() -> None:
    assert _types("паспорт 4510 123456") == [EntityType.DOC_ID]


def test_email_wins_over_embedded_phone() -> None:
    # «+7900...» внутри email-адреса относится к адресу, а не к телефону
    spans = detect_strict("пишите на user+79001234567@example.com")
    assert [s.entity_type for s in spans] == [EntityType.EMAIL]


def test_normalize_phone_8_to_7() -> None:
    assert normalize_phone("+7 916 253-47-81") == "79162534781"
    assert normalize_phone("8 (916) 253 47 81") == "79162534781"


async def test_strict_anonymizer_repeats_get_same_marker() -> None:
    anonymizer = StrictRulesAnonymizer()
    text = "Тел. +7 916 253-47-81, дублирую: 8 (916) 253-47-81, почта ivan@example.com"
    result = await anonymizer.anonymize(text, user_id="u1", context_id="c1")

    assert result.text == "Тел. PHONE_1, дублирую: PHONE_1, почта EMAIL_1"
    assert [m.marker for m in result.markers] == ["PHONE_1", "EMAIL_1"]
    assert result.markers[0].normalized_value == "79162534781"


async def test_strict_anonymizer_numbering_per_type() -> None:
    anonymizer = StrictRulesAnonymizer()
    result = await anonymizer.anonymize(
        "a@ex.com, b@ex.com, +7 900 111-11-11", user_id="u1", context_id="c1"
    )
    assert result.text == "EMAIL_1, EMAIL_2, PHONE_1"


async def test_strict_anonymizer_keeps_text_outside_spans() -> None:
    anonymizer = StrictRulesAnonymizer()
    text = "Заказ №1234567890 принят; тел. +7 916 253-47-81"
    result = await anonymizer.anonymize(text, user_id="u1", context_id="c1")
    assert "Заказ №1234567890 принят;" in result.text
    assert "PHONE_1" in result.text
