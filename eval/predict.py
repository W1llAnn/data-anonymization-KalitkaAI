"""Инференс NER-модели: текст → спаны сущностей.

Согласовано со схемой разметки обучения (eval/bio.py): предсказания читаются
только на первых сабтокенах слов (между токенами был пробел), спан расширяется
на всё слово — сабтокены-продолжения в обучении замаскированы и их метки
недостоверны.

Запуск:
    python -m eval.predict --model eval/checkpoints/c1/best --text "текст..."
"""

from __future__ import annotations

import argparse

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer


def predict_spans(
    text: str, tokenizer: AutoTokenizer, model: AutoModelForTokenClassification
) -> list[tuple[str, int, int]]:
    """Возвращает спаны (тип, начало, конец) в символах исходного текста.

    Предсказания читаются только на первых сабтокенах слов (группировка по
    word_ids — как при разметке обучения); спан расширяется на весь диапазон
    символов слова, сабтокены-продолжения меток не несут.
    """
    encoding = tokenizer(
        text, return_tensors="pt", return_offsets_mapping=True, truncation=True, max_length=512
    )
    offsets = encoding.pop("offset_mapping")[0].tolist()
    word_ids = encoding.word_ids(0)
    model.eval()
    with torch.inference_mode():
        logits = model(**encoding).logits[0]
    tags = [model.config.id2label[index] for index in logits.argmax(-1).tolist()]

    spans: list[tuple[str, int, int]] = []
    open_type: str | None = None
    start = end = -1
    previous_word: int | None = None

    for tag, word_id, (token_start, token_end) in zip(tags, word_ids, offsets, strict=True):
        if word_id is None:  # спецтокены
            continue
        word_first = word_id != previous_word
        if word_first:
            if tag.startswith("B-"):
                if open_type is not None:
                    spans.append((open_type, start, end))
                open_type, start = tag[2:], token_start
            elif tag.startswith("I-") and open_type == tag[2:]:
                pass  # продолжение сущности на новом слове
            else:
                if open_type is not None:
                    spans.append((open_type, start, end))
                    open_type = None
        if open_type is not None:
            end = token_end  # сабтокены-продолжения расширяют спан на всё слово
        previous_word = word_id

    if open_type is not None:
        spans.append((open_type, start, end))
    return spans


def main() -> None:
    parser = argparse.ArgumentParser(description="Спаны ПДн в тексте обученной моделью")
    parser.add_argument("--model", default="eval/checkpoints/c1/best")
    parser.add_argument("--text", required=True)
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForTokenClassification.from_pretrained(args.model)
    for entity, start, end in predict_spans(args.text, tokenizer, model):
        print(f"{entity:8} → {args.text[start:end]!r}")


if __name__ == "__main__":
    main()
