"""Детектор персон по словарю имён/фамилий и морфологии (NAME_DICT-этап).

Кандидат — два соседних слова с заглавной буквы; проверяем леммы: пара
«имя + фамилия» в любом порядке. Отдельные имена не детектим («Любовь к
природе» — не персона): это страховочный словарь, роль модели — неделя 6+.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pymorphy3

from anongw.contracts import EntityType, Span

_DATA_DIR = Path(__file__).parent / "data"


def _load(name: str) -> frozenset[str]:
    text = (_DATA_DIR / name).read_text(encoding="utf-8")
    return frozenset(line.strip() for line in text.splitlines() if line.strip())


_FIRST_NAMES = _load("first_names.txt")
_SURNAMES = _load("surnames.txt")

_CAP_WORD_RE = re.compile(r"\b[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\b")

_morph: pymorphy3.MorphAnalyzer | None = None


def _analyzer() -> pymorphy3.MorphAnalyzer:
    global _morph
    if _morph is None:
        _morph = pymorphy3.MorphAnalyzer()
    return _morph


@lru_cache(maxsize=4096)
def lemma(word: str) -> str:
    """Лемма слова в нижнем регистре (кэш: морфология не быстрая)."""
    parses = _analyzer().parse(word)
    return parses[0].normal_form.lower() if parses else word.lower()


def detect_persons(text: str) -> list[Span]:
    """Пары соседних слов с заглавной. Идём по всем парам, а не по непересекающимся
    матчам: иначе капитализованное слово перед парой («Встречайте Анну Смирнову»)
    съест вторую половину настоящей пары.
    """
    words = [(m.group(0), m.start(), m.end()) for m in _CAP_WORD_RE.finditer(text)]
    spans: list[Span] = []
    for (first, start, first_end), (second, second_start, end) in zip(
        words, words[1:], strict=False
    ):
        if second_start != first_end + 1:  # между словами ровно один пробел
            continue
        lemma_first, lemma_second = lemma(first), lemma(second)
        if (lemma_first in _FIRST_NAMES and lemma_second in _SURNAMES) or (
            lemma_first in _SURNAMES and lemma_second in _FIRST_NAMES
        ):
            spans.append(Span(start, end, EntityType.PERSON, text[start:end]))
    return spans
