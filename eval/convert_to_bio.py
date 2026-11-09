"""Конвертация JSONL-разметки в BIO (docs/training.md §4).

Запуск:
    python -m eval.convert_to_bio --src dataset/train/train_1k.jsonl --out dataset/train/bio
Выход: train.jsonl и dev.jsonl (сплит 90/10, seed 42) с полями input_ids/labels.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from transformers import AutoTokenizer

from eval.bio import encode_example


def main() -> None:
    parser = argparse.ArgumentParser(description="JSONL → BIO для токен-классификации")
    parser.add_argument("--src", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("dataset/train/bio"))
    parser.add_argument("--tokenizer", default="cointegrated/rubert-tiny2")
    parser.add_argument("--dev-frac", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer)
    rows = [
        json.loads(line)
        for line in args.src.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    converted = []
    conflicts = 0
    for row in rows:
        encoded = encode_example(row["text"], row["entities"], tokenizer)
        # контроль конфликтов: у каждой сущности должен быть хотя бы один тег != O/-100
        labeled = {label for label in encoded["labels"] if label > 0}
        if row["entities"] and not labeled:
            conflicts += 1
            continue
        converted.append(encoded)

    rng = random.Random(args.seed)
    rng.shuffle(converted)
    dev_size = max(1, int(len(converted) * args.dev_frac))
    splits = {"dev": converted[:dev_size], "train": converted[dev_size:]}

    args.out.mkdir(parents=True, exist_ok=True)
    for name, data in splits.items():
        path = args.out / f"{name}.jsonl"
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            for item in data:
                stream.write(json.dumps(item) + "\n")
        print(f"{path}: {len(data)} примеров")

    if conflicts:
        print(f"ПРОПУЩЕНО (сущности не легли на токены): {conflicts}")


if __name__ == "__main__":
    main()
