"""Span-метрики токен-классификации: точное совпадение спанов (docs/training.md §9).

Замена seqeval: склеиваем последовательности B-/I- меток в спаны (start, type),
сравниваем точным совпадением, считаем precision / recall / F1 по типам и macro.
"""

from __future__ import annotations

from collections.abc import Iterable

from eval.bio import ID2LABEL

Span = tuple[int, int, str]  # (начало, конец, тип) в токенах, конец исключающий


def extract_spans(label_ids: Iterable[int]) -> list[Span]:
    """Собирает спаны из последовательности id меток (-100 и O разрываются)."""
    ids = list(label_ids)
    spans: list[Span] = []
    start: int | None = None
    etype: str | None = None
    for position, label_id in enumerate(ids):
        tag = ID2LABEL.get(label_id, "O") if label_id >= 0 else "O"
        if tag.startswith("B-"):
            if start is not None and etype is not None:
                spans.append((start, position, etype))
            start, etype = position, tag[2:]
        elif tag.startswith("I-") and start is not None and tag[2:] == etype:
            continue
        else:
            if start is not None and etype is not None:
                spans.append((start, position, etype))
            start, etype = None, None
    if start is not None and etype is not None:
        spans.append((start, len(ids), etype))
    return spans


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def span_metrics(
    true_ids: list[list[int]], pred_ids: list[list[int]]
) -> dict[str, dict[str, float]]:
    """Precision/recall/F1: по каждому типу + macro. Совпадение спана точное."""
    per_type: dict[str, dict[str, int]] = {}

    def bucket(entity: str) -> dict[str, int]:
        return per_type.setdefault(entity, {"tp": 0, "fp": 0, "fn": 0})

    for truth, prediction in zip(true_ids, pred_ids, strict=True):
        gold = set(extract_spans(truth))
        found = set(extract_spans(prediction))
        for span in gold & found:
            bucket(span[2])["tp"] += 1
        for span in found - gold:
            bucket(span[2])["fp"] += 1
        for span in gold - found:
            bucket(span[2])["fn"] += 1

    result: dict[str, dict[str, float]] = {}
    for entity, counts in sorted(per_type.items()):
        precision, recall, f1 = _prf(counts["tp"], counts["fp"], counts["fn"])
        result[entity] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": counts["tp"] + counts["fn"],
        }
    macro = {
        "precision": round(sum(v["precision"] for v in result.values()) / len(result), 4)
        if result
        else 0.0,
        "recall": round(sum(v["recall"] for v in result.values()) / len(result), 4)
        if result
        else 0.0,
        "f1": round(sum(v["f1"] for v in result.values()) / len(result), 4) if result else 0.0,
    }
    result["macro"] = macro
    return result
