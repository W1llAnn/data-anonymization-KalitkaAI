"""Оценка модели на dev: span-метрики по типам + запись в experiments.jsonl.

Запуск:
    python -m eval.evaluate --model eval/checkpoints/c1/best --bio dataset/train/bio \
        --participant "C1-rubert-tiny2" --lr 1e-4 --dataset train_1k-seed-1001
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForTokenClassification

from eval.metrics import span_metrics


class BioDataset(Dataset):
    def __init__(self, path: Path) -> None:
        self.rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, list[int]]:
        row = self.rows[index]
        return {"input_ids": row["input_ids"], "labels": row["labels"]}


def collate(batch: list[dict[str, list[int]]]) -> dict[str, torch.Tensor]:
    max_len = max(len(row["input_ids"]) for row in batch)
    pad = 0
    inputs, labels, masks = [], [], []
    for row in batch:
        gap = max_len - len(row["input_ids"])
        inputs.append(row["input_ids"] + [pad] * gap)
        masks.append([1] * len(row["input_ids"]) + [0] * gap)
        labels.append(row["labels"] + [-100] * gap)
    return {
        "input_ids": torch.tensor(inputs),
        "attention_mask": torch.tensor(masks),
        "labels": torch.tensor(labels),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Оценка NER на dev")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--bio", type=Path, default=Path("dataset/train/bio"))
    parser.add_argument("--participant", required=True)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--dataset", default="")
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--reports", type=Path, default=Path("eval/reports/experiments.jsonl"))
    args = parser.parse_args()

    model = AutoModelForTokenClassification.from_pretrained(args.model)
    model.eval()

    dev = BioDataset(args.bio / "dev.jsonl")
    loader = DataLoader(dev, batch_size=args.batch, shuffle=False, collate_fn=collate)

    all_true: list[list[int]] = []
    all_pred: list[list[int]] = []
    with torch.inference_mode():
        for batch in loader:
            logits = model(
                input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]
            ).logits
            predicted = torch.argmax(logits, dim=-1)
            for truth, prediction in zip(batch["labels"], predicted, strict=True):
                keep = truth != -100  # паддинг исключаем, предсказания на нём не сравниваем
                all_true.append(truth[keep].tolist())
                all_pred.append(prediction[keep].tolist())

    metrics = span_metrics(all_true, all_pred)

    print(f"{'тип':10} {'P':>7} {'R':>7} {'F1':>7} {'шт':>5}")
    for entity, values in metrics.items():
        support = values.get("support", "")
        line = f"{entity:10} {values['precision']:7.3f} {values['recall']:7.3f}"
        print(f"{line} {values['f1']:7.3f} {support!s:>5}")

    entry = {
        "participant": args.participant,
        "model": str(args.model),
        "lr": args.lr,
        "dataset": args.dataset,
        "dev_size": len(dev),
        "metrics": metrics,
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    args.reports.parent.mkdir(parents=True, exist_ok=True)
    with args.reports.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Записано: {args.reports}")


if __name__ == "__main__":
    main()
