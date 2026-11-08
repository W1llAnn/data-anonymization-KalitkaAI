"""CLI генератора: python -m dataset.generator --count 150 --seed 303 --export 10"""

from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import asdict
from pathlib import Path

from dataset.generator.export_files import export_example
from dataset.generator.templates import build_control_example, build_example

ENTITY_ORDER = ["PERSON", "PHONE", "EMAIL", "ADDRESS", "DOC_ID"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Генератор синтетических примеров датасета")
    parser.add_argument("--count", type=int, default=10, help="количество примеров")
    parser.add_argument("--seed", type=int, default=42, help="сид генератора (воспроизводимость)")
    parser.add_argument("--split", choices=["train", "control"], default="train")
    parser.add_argument("--out", type=Path, default=Path("dataset/samples/samples.jsonl"))
    parser.add_argument("--registry", type=Path, default=Path("dataset/samples/registry.csv"))
    parser.add_argument(
        "--export",
        type=int,
        default=0,
        help="выгрузить первые N примеров файлами (7 txt / 3 docx на каждые 10)",
    )
    parser.add_argument("--export-dir", type=Path, default=Path("dataset/files"))
    args = parser.parse_args()

    rng = random.Random(args.seed)
    build = build_control_example if args.split == "control" else build_example
    examples = [build(rng, i) for i in range(args.count)]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="\n") as stream:
        for example in examples:
            record = asdict(example)
            record["id"] = record.pop("example_id")  # поле схемы — «id»
            record["entities"] = [asdict(span) for span in example.entities]
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    exported_formats: dict[str, str] = {}
    for position, example in enumerate(examples[: args.export]):
        as_docx = position % 10 >= 7  # 7 txt + 3 docx на каждые 10
        export_example(args.export_dir, example.example_id, example.text, as_docx)
        exported_formats[example.example_id] = "docx" if as_docx else "txt"

    counts_by_type = {etype: 0 for etype in ENTITY_ORDER}
    for example in examples:
        for span in example.entities:
            counts_by_type[span.entity_type] += 1

    args.registry.parent.mkdir(parents=True, exist_ok=True)
    with args.registry.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ["example_id", "genre", "template", "format", "split", "n_entities", *ENTITY_ORDER]
        )
        for example in examples:
            per_type = [
                sum(1 for s in example.entities if s.entity_type == t) for t in ENTITY_ORDER
            ]
            writer.writerow(
                [
                    example.example_id,
                    example.genre,
                    example.template,
                    exported_formats.get(example.example_id, "text"),
                    args.split,
                    len(example.entities),
                    *per_type,
                ]
            )

    total_entities = sum(counts_by_type.values())
    print(f"Примеров: {len(examples)}, сущностей: {total_entities}, по типам: {counts_by_type}")
    if args.export:
        print(f"Файлы: {args.export_dir} ({len(exported_formats)} шт.)")
    print(f"JSONL: {args.out}")
    print(f"Реестр: {args.registry}")


if __name__ == "__main__":
    main()
