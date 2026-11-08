"""Проверки детекторов адресов и персон (неделя 3, пуш 2, Р2)."""

from __future__ import annotations

import pytest

from anongw.anonymizer.normalize import normalize_address, normalize_person
from anongw.anonymizer.persistent import PersistentAnonymizer
from anongw.anonymizer.rules import detect
from anongw.contracts import EntityType

pytestmark = pytest.mark.unit


def _types(text: str) -> list[EntityType]:
    return [span.entity_type for span in detect(text)]


# --- Адреса ---


def test_full_address_detected() -> None:
    text = "Проживает: г. Тверь, ул. Мира, д. 7, кв. 12"
    spans = detect(text)
    assert _types(text) == [EntityType.ADDRESS]
    assert spans[0].text == "г. Тверь, ул. Мира, д. 7, кв. 12"


def test_street_without_city_detected() -> None:
    assert _types("Офис: ул. Ленина, д. 15") == [EntityType.ADDRESS]


def test_city_with_street() -> None:
    assert _types("г. Москва, пр-т Мира") == [EntityType.ADDRESS]


def test_random_words_not_address() -> None:
    assert detect("Городская стража дома 7") == []


# --- Персоны ---


def test_person_nominative_detected() -> None:
    assert _types("Заявление подал Иван Петров") == [EntityType.PERSON]


def test_person_in_declined_cases() -> None:
    assert _types("Письмо адресовано Ивану Петрову") == [EntityType.PERSON]
    assert _types("Встречайте Анну Смирнову") == [EntityType.PERSON]


def test_surname_first_order_detected() -> None:
    assert _types("Подпись: Петров Иван") == [EntityType.PERSON]


def test_unknown_words_not_person() -> None:
    # Иван — в словаре, «магазин» — нет; «Иванов Петрович» — фамилия+отчество, не пара имя-фамилия
    assert detect("Иван магазин") == []
    assert detect("Иванов Петрович") == []


# --- Нормализация ---


def test_person_normalization_lemmas() -> None:
    # pymorphy приводит женские фамилии к мужской лемме — консистентно для всех падежей
    assert normalize_person("Ивану Петрову") == "иван петров"
    assert normalize_person("Иван Петров") == "иван петров"
    assert normalize_person("Анной Смирновой") == normalize_person("Анна Смирнова")
    assert normalize_person("Анна Смирнова") == "анна смирнов"


def test_address_normalization_expands_abbreviations() -> None:
    assert (
        normalize_address("г. Тверь, ул. Мира, д. 7, кв. 12")
        == "город тверь улица мира дом 7 квартира 12"
    )
    assert normalize_address("ул. Ленина, д. 15") == normalize_address("улица Ленина, дом 15")


# --- Сквозная консистентность ---


async def test_full_pipeline_person_and_address(tmp_path) -> None:
    from anongw.mapping.sqlite_store import SqliteMappingStore

    store = SqliteMappingStore(str(tmp_path / "m.db"))
    anonymizer = PersistentAnonymizer(store)

    first = await anonymizer.anonymize(
        "Письмо для Ивану Петрову, г. Тверь, ул. Мира, д. 7", user_id="u1", context_id="ctx"
    )
    second = await anonymizer.anonymize(
        "Иван Петров подтвердил адрес: г. Тверь, ул. Мира, д. 7",
        user_id="u1",
        context_id="ctx",
    )

    assert first.text == "Письмо для PERSON_1, ADDRESS_1"
    # Разные падежи имени и тот же адрес — прежние маркеры
    assert "PERSON_1" in second.text
    assert "ADDRESS_1" in second.text
