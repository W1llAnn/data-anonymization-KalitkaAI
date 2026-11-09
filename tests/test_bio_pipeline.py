"""Проверки BIO-конвейера: метрики спанов и кодирование примеров (Р2, неделя 4)."""

from __future__ import annotations

import pytest
from eval.bio import LABEL2ID, LABELS, encode_example
from eval.metrics import extract_spans, span_metrics

pytestmark = pytest.mark.unit


def test_labels_schema() -> None:
    # O + B/I × 5 типов = 11 меток, порядок фиксирован (id меток модели)
    assert LABELS[0] == "O"
    assert len(LABELS) == 11
    assert LABEL2ID["B-PERSON"] < LABEL2ID["I-PERSON"] < LABEL2ID["B-PHONE"]


def test_extract_spans_assembles_and_breaks() -> None:
    b, i = LABEL2ID["B-PERSON"], LABEL2ID["I-PERSON"]
    o, phone = LABEL2ID["O"], LABEL2ID["B-PHONE"]

    spans = extract_spans([o, b, i, i, o, phone, -100])

    assert spans == [(1, 4, "PERSON"), (5, 6, "PHONE")]


def test_extract_spans_i_without_b_is_ignored() -> None:
    i = LABEL2ID["I-PERSON"]
    assert extract_spans([i, i, LABEL2ID["O"]]) == []


def test_span_metrics_perfect_prediction() -> None:
    truth = [[LABEL2ID["B-PERSON"], LABEL2ID["I-PERSON"], LABEL2ID["O"]]]
    metrics = span_metrics(truth, [list(truth[0])])

    assert metrics["PERSON"]["f1"] == 1.0
    assert metrics["macro"]["f1"] == 1.0


def test_span_metrics_counts_fp_and_fn() -> None:
    truth = [[LABEL2ID["B-PERSON"], LABEL2ID["O"], LABEL2ID["B-EMAIL"]]]
    prediction = [[LABEL2ID["B-PERSON"], LABEL2ID["O"], LABEL2ID["B-PHONE"]]]

    metrics = span_metrics(truth, prediction)

    assert metrics["PERSON"] == {"precision": 1.0, "recall": 1.0, "f1": 1.0, "support": 1}
    assert metrics["EMAIL"]["support"] == 1
    assert metrics["EMAIL"]["recall"] == 0.0  # пропущенная сущность
    assert metrics["PHONE"]["precision"] == 0.0  # ложное срабатывание
    assert 0 < metrics["macro"]["f1"] < 1


@pytest.mark.ml
def test_encode_example_first_subtoken_only() -> None:
    """Первый сабтокен слова — B/I, продолжения — -100, спецтокены — -100."""
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained("cointegrated/rubert-tiny2")
    text = "Ивану Петрову звонили"
    entities = [{"start": 0, "end": 13, "entity_type": "PERSON", "text": "Ивану Петрову"}]

    encoded = encode_example(text, entities, tokenizer)

    assert encoded["input_ids"][0] == tokenizer.cls_token_id  # [CLS]
    assert encoded["labels"][0] == -100
    assert encoded["labels"][-1] == -100  # [SEP]
    labeled = [label for label in encoded["labels"] if label > 0]
    assert all(label in (LABEL2ID["B-PERSON"], LABEL2ID["I-PERSON"]) for label in labeled)
    assert LABEL2ID["B-PERSON"] in labeled
