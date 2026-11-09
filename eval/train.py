"""Обучение NER-модели по протоколу docs/training.md §5–9.

Пресеты участников линейки (§5): модель и lr по умолчанию.
    python -m eval.train --participant C1            # rubert-tiny2, lr 1e-4 (CPU)
    python -m eval.train --participant C2            # rubert-base, lr 3e-5 (GPU 4–6 ГБ)
Каждый прогон автоматически дописывается в eval/reports/experiments.jsonl (§9).
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from torch.utils.data import Dataset
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
    set_seed,
)

from eval.bio import LABELS
from eval.metrics import span_metrics

# Линейка моделей (training.md §5): участник → (модель, lr по протоколу §6)
PRESETS: dict[str, tuple[str, float]] = {
    "C1": ("cointegrated/rubert-tiny2", 1e-4),
    "C2": ("DeepPavlov/rubert-base-cased", 3e-5),
    "C3": ("xlm-roberta-base", 3e-5),
}


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
        return {
            "input_ids": row["input_ids"],
            "labels": row["labels"],
        }


def compute_metrics(prediction) -> dict[str, float]:
    logits = prediction.predictions
    labels = prediction.label_ids
    if isinstance(logits, tuple):
        logits = logits[0]
    predicted = np.argmax(logits, axis=-1)
    # на -100-позициях (сабтокены-продолжения, спецтокены) предсказания не сравниваем
    predicted = np.where(labels == -100, -100, predicted)
    metrics = span_metrics(labels.tolist(), predicted.tolist())
    return {
        "precision": metrics["macro"]["precision"],
        "recall": metrics["macro"]["recall"],
        "f1": metrics["macro"]["f1"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Обучение токен-классификации")
    parser.add_argument("--participant", choices=sorted(PRESETS), default="C1")
    parser.add_argument("--bio", type=Path, default=Path("dataset/train/bio"))
    parser.add_argument(
        "--out", type=Path, default=None, help="по умолчанию eval/checkpoints/<participant>"
    )
    parser.add_argument("--model", default=None, help="переопределить модель пресета")
    parser.add_argument("--lr", type=float, default=None, help="по умолчанию — lr пресета")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cpu", action="store_true", default=True)
    args = parser.parse_args()

    model_name = args.model or PRESETS[args.participant][0]
    learning_rate = args.lr if args.lr is not None else PRESETS[args.participant][1]
    out_dir = args.out or Path(f"eval/checkpoints/{args.participant.lower()}")

    set_seed(args.seed)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(
        model_name,
        num_labels=len(LABELS),
        id2label=dict(enumerate(LABELS)),
        label2id={label: i for i, label in enumerate(LABELS)},
    )

    train_set = BioDataset(args.bio / "train.jsonl")
    dev_set = BioDataset(args.bio / "dev.jsonl")
    print(f"участник: {args.participant} ({model_name}), lr={learning_rate}")
    print(f"train: {len(train_set)}, dev: {len(dev_set)}, меток: {len(LABELS)}")

    steps_per_epoch = max(1, len(train_set) // args.batch)
    warmup_steps = int(0.1 * steps_per_epoch * args.epochs)  # warmup 10% (протокол §6)

    training_args = TrainingArguments(
        output_dir=str(out_dir),
        num_train_epochs=args.epochs,
        learning_rate=learning_rate,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=args.batch,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        save_total_limit=2,
        logging_steps=20,
        warmup_steps=warmup_steps,
        weight_decay=0.01,
        seed=args.seed,
        use_cpu=args.cpu,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_set,
        eval_dataset=dev_set,
        data_collator=DataCollatorForTokenClassification(tokenizer),
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
    )

    trainer.train()
    best_dir = out_dir / "best"
    trainer.save_model(str(best_dir))
    tokenizer.save_pretrained(str(best_dir))
    print(f"Лучшая модель сохранена: {best_dir}")

    _log_experiment(
        participant=f"{args.participant}-{model_name.split('/')[-1]}",
        best_dir=best_dir,
        learning_rate=learning_rate,
        bio_dir=args.bio,
        seed=args.seed,
        dev_size=len(dev_set),
        metrics=_final_metrics(trainer, dev_set),
    )


def _final_metrics(trainer: Trainer, dev_set: BioDataset) -> dict[str, dict[str, float]]:
    """Финальные span-метрики лучшей модели на dev (по типам + macro)."""
    prediction = trainer.predict(dev_set)
    return span_metrics(
        prediction.label_ids.tolist(), np.argmax(prediction.predictions, axis=-1).tolist()
    )


def _log_experiment(
    *,
    participant: str,
    best_dir: Path,
    learning_rate: float,
    bio_dir: Path,
    seed: int,
    dev_size: int,
    metrics: dict[str, dict[str, float]],
) -> None:
    """Автологирование прогона в experiments.jsonl — протокол §9."""
    record = {
        "participant": participant,
        "model": str(best_dir),
        "lr": learning_rate,
        "dataset": f"{bio_dir.name}-seed-{seed}",
        "dev_size": dev_size,
        "metrics": metrics,
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    report_path = Path("eval/reports/experiments.jsonl")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Прогон записан: {report_path}")


if __name__ == "__main__":
    main()
