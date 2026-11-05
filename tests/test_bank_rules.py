"""Проверки банковских детекторов: карты (Лун) и счета (контекстное слово)."""

from __future__ import annotations

import random

import pytest
from dataset.generator.pii_gen import generate_account, generate_card

from anongw.anonymizer.rules import detect_strict
from anongw.anonymizer.strict import StrictRulesAnonymizer
from anongw.contracts import EntityType

pytestmark = pytest.mark.unit


def _doc_texts(text: str) -> list[str]:
    return [s.text for s in detect_strict(text) if s.entity_type == EntityType.DOC_ID]


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_generated_card_grouped_found(seed: int) -> None:
    card = generate_card(random.Random(seed), grouped=True)
    assert _doc_texts(f"Оплата на карту {card}, спасибо") == [card]


@pytest.mark.parametrize("seed", [1, 2])
def test_generated_card_plain_found(seed: int) -> None:
    card = generate_card(random.Random(seed), grouped=False)
    assert _doc_texts(f"карта {card}") == [card]


def test_card_with_dashes_found() -> None:
    card = generate_card(random.Random(7), grouped=True).replace(" ", "-")
    assert _doc_texts(f"карта {card}") == [card]


def test_invalid_card_not_found() -> None:
    # Валидная карта с изменённой последней цифрой — Лун не сходится
    valid = generate_card(random.Random(1), grouped=False)
    broken = valid[:-1] + str((int(valid[-1]) + 1) % 10)
    assert _doc_texts(f"карта {broken}") == []


def test_account_with_context_word_found() -> None:
    account = generate_account(random.Random(1))
    assert _doc_texts(f"Расчётный счёт №{account}") == [account]
    assert _doc_texts(f"переведите на счет {account}") == [account]


def test_bare_account_digits_not_found() -> None:
    # Голые 20 цифр неоднозначны: без слова «счёт» не детектим
    account = generate_account(random.Random(2))
    assert _doc_texts(f"код операции {account}") == []


async def test_card_formats_get_same_marker() -> None:
    card = generate_card(random.Random(3))
    plain = card.replace(" ", "")
    result = await StrictRulesAnonymizer().anonymize(
        f"карта {card}, повторю слитно: {plain}", user_id="u1", context_id="c1"
    )
    assert result.text == "карта DOC_ID_1, повторю слитно: DOC_ID_1"
