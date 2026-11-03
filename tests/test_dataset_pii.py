"""Кросс-проверки датасета и детекторов Р2 (неделя 2, пуш 3, Р3)."""

from __future__ import annotations

import random

import pytest
from dataset.generator.pii_gen import generate_inn10, generate_inn12, generate_snils
from dataset.generator.templates import build_example

from anongw.anonymizer.rules import detect_strict
from anongw.contracts import EntityType

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_generated_inn10_found_by_detector(seed: int) -> None:
    value = generate_inn10(random.Random(seed))
    spans = detect_strict(f"ИНН {value}")
    assert [(s.entity_type, s.text) for s in spans] == [(EntityType.DOC_ID, value)]


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_generated_inn12_found_by_detector(seed: int) -> None:
    value = generate_inn12(random.Random(seed))
    spans = detect_strict(f"ИНН {value}")
    assert [(s.entity_type, s.text) for s in spans] == [(EntityType.DOC_ID, value)]


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_generated_snils_found_by_detector(seed: int) -> None:
    value = generate_snils(random.Random(seed))
    spans = detect_strict(f"СНИЛС {value}")
    assert [(s.entity_type, s.text) for s in spans] == [(EntityType.DOC_ID, value)]


def test_build_example_variety() -> None:
    rng = random.Random(42)
    templates_seen: set[str] = set()
    for index in range(30):
        example = build_example(rng, index)
        assert example.text
        for span in example.entities:
            assert example.text[span.start : span.end] == span.text
        templates_seen.add(example.template)
    # Расширенный набор шаблонов реально используется
    assert len(templates_seen) >= 5
