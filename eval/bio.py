"""Общие определения BIO-разметки для токен-классификации (docs/training.md §3)."""

from __future__ import annotations

from typing import Any

ENTITY_TYPES = ["PERSON", "PHONE", "EMAIL", "ADDRESS", "DOC_ID"]

# O + B/I на каждый тип; порядок фиксирован — он же порядок id меток модели
LABELS: list[str] = ["O"] + [f"{prefix}-{etype}" for etype in ENTITY_TYPES for prefix in ("B", "I")]

LABEL2ID: dict[str, int] = {label: i for i, label in enumerate(LABELS)}
ID2LABEL: dict[int, str] = dict(enumerate(LABELS))


def encode_example(
    text: str, entities: list[dict[str, Any]], tokenizer: Any
) -> dict[str, list[int]]:
    """Кодирует пример в input_ids + метки по смещениям токенов.

    Правила (marker-scheme/training.md §3): слова группируются по word_ids
    токенизатора (WordPiece режет и по пунктуации, поэтому пробелов мало);
    первый сабтокен слова получает B/I, продолжения слова маскируются (-100),
    спецтокены — -100, вне сущностей — O.
    """
    encoding = tokenizer(text, return_offsets_mapping=True, truncation=True, max_length=512)
    offsets: list[tuple[int, int]] = encoding["offset_mapping"]
    word_ids: list[int | None] = encoding.word_ids()
    spans = sorted(entities, key=lambda e: e["start"])

    labels: list[int] = []
    previous_word: int | None = None
    for position, word_id in enumerate(word_ids):
        if word_id is None:  # [CLS]/[SEP]/[PAD]
            labels.append(-100)
            continue
        token_start = offsets[position][0]
        word_first = word_id != previous_word
        entity = next((s for s in spans if s["start"] <= token_start < s["end"]), None)
        if entity is None:
            labels.append(LABEL2ID["O"])
        elif not word_first:
            labels.append(-100)  # продолжение слова (следующий сабтокен)
        elif token_start == entity["start"]:
            labels.append(LABEL2ID[f"B-{entity['entity_type']}"])
        else:
            labels.append(LABEL2ID[f"I-{entity['entity_type']}"])
        previous_word = word_id

    return {"input_ids": encoding["input_ids"], "labels": labels}
