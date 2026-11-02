"""Проверки каркасных реализаций контрактов из anongw.contracts."""

from __future__ import annotations

import pytest

from anongw.anonymizer.service import PassThroughAnonymizer
from anongw.contracts import EntityType, Marker
from anongw.mapping.store import InMemoryMappingStore
from anongw.restorer.service import MappingRestorer

pytestmark = pytest.mark.unit


async def test_passthrough_anonymizer_keeps_text() -> None:
    anonymizer = PassThroughAnonymizer()
    result = await anonymizer.anonymize(
        "Иван Петров, +7 900 000-00-00", user_id="u1", context_id="c1"
    )
    assert result.text == "Иван Петров, +7 900 000-00-00"
    assert result.markers == ()


async def test_restorer_replaces_only_known_marker() -> None:
    store = InMemoryMappingStore()
    await store.put("u1", "c1", Marker("PERSON_1", EntityType.PERSON, "Иван Петров"))
    restorer = MappingRestorer(store)

    restored = await restorer.restore("PERSON_1 написал на EMAIL_1", user_id="u1", context_id="c1")

    assert restored == "Иван Петров написал на EMAIL_1"


async def test_mapping_isolated_by_user_and_context() -> None:
    store = InMemoryMappingStore()
    await store.put("u1", "c1", Marker("PERSON_1", EntityType.PERSON, "Иван"))

    assert await store.get("u2", "c1", "PERSON_1") is None
    assert await store.get("u1", "c2", "PERSON_1") is None
    assert await store.get("u1", "c1", "PERSON_1") is not None
