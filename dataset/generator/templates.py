"""Шаблоны трёх жанров: письма, документы, фрагменты интервью.

Каждый шаблон — функция, собирающая текст из частей (строки и Slot).
Границы спанов и повторные упоминания (одинаковый entity_id) отслеживает render.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from dataset.generator.pools import (
    CITIES,
    DOMAINS,
    EMAIL_LOCALS,
    NAME_FORMS,
    STREETS,
)
from dataset.generator.render import EntitySpan, Slot, render_parts


@dataclass(frozen=True)
class Example:
    example_id: str
    genre: str
    template: str
    text: str
    entities: tuple[EntitySpan, ...]


def _phone(rng: random.Random) -> str:
    return (
        f"+7 9{rng.randint(10, 99)} {rng.randint(100, 999)}-"
        f"{rng.randint(10, 99)}-{rng.randint(10, 99)}"
    )


def _email(rng: random.Random) -> str:
    return f"{rng.choice(EMAIL_LOCALS)}@{rng.choice(DOMAINS)}"


def _address(rng: random.Random) -> str:
    address = f"г. {rng.choice(CITIES)}, ул. {rng.choice(STREETS)}, д. {rng.randint(1, 99)}"
    if rng.random() < 0.5:
        address += f", кв. {rng.randint(1, 200)}"
    return address


def _passport(rng: random.Random) -> str:
    return f"{rng.randint(1000, 9999)} {rng.randint(100000, 999999)}"


def _snils(rng: random.Random) -> str:
    return (
        f"{rng.randint(100, 999)}-{rng.randint(100, 999)}-"
        f"{rng.randint(100, 999)} {rng.randint(10, 99)}"
    )


def build_letter(rng: random.Random, index: int) -> Example:
    person = rng.choice(NAME_FORMS)
    parts: list[str | Slot]
    if rng.random() < 0.2:
        # Вариант без ПДн (обязательная категория ТЗ)
        parts = [
            "Здравствуйте!\n\n",
            f"Направляю отчёт по договору №{rng.randint(100, 999)} на согласование. ",
            f"Жду замечаний до {rng.randint(10, 28)}.11.2026.\n\n",
            "С уважением,\nОтдел делопроизводства",
        ]
        template = "letter_plain"
    else:
        parts = [
            "Здравствуйте, ",
            Slot("PERSON", person["dat"], "e1"),
            "!\n\n",
            f"Направляю акт сверки по договору №{rng.randint(100, 999)}. ",
            f"Просьба подписать и вернуть до {rng.randint(10, 28)}.12.2026.\n\n",
            "Связь со мной: тел. ",
            Slot("PHONE", _phone(rng), "e2"),
            ", почта ",
            Slot("EMAIL", _email(rng), "e3"),
            ".\n\nС уважением,\n",
            Slot("PERSON", person["nom"], "e1"),
            "\n",
        ]
        template = "letter_contact"
    text, spans = render_parts(parts)
    return Example(f"ex_{index:04d}", "letter", template, text, tuple(spans))


def build_document(rng: random.Random, index: int) -> Example:
    person = rng.choice(NAME_FORMS)
    doc = _passport(rng) if rng.random() < 0.5 else _snils(rng)
    parts: list[str | Slot] = [
        "СПРАВКА\n\n",
        "Дана ",
        Slot("PERSON", person["dat"], "e1"),
        ", паспорт/СНИЛС ",
        Slot("DOC_ID", doc, "e2"),
        ", проживающему по адресу: ",
        Slot("ADDRESS", _address(rng), "e3"),
        ".\n\n",
        "Справка выдана для предъявления по месту требования.\n\n",
        "Контакты для связи: ",
        Slot("PHONE", _phone(rng), "e4"),
        ", ",
        Slot("EMAIL", _email(rng), "e5"),
        ".",
    ]
    text, spans = render_parts(parts)
    return Example(f"ex_{index:04d}", "document", "document_cert", text, tuple(spans))


def build_interview(rng: random.Random, index: int) -> Example:
    person = rng.choice(NAME_FORMS)
    parts: list[str | Slot] = [
        "Интервью с ",
        Slot("PERSON", person["nom"], "e1"),
        "\n\n",
        "— Где вы сейчас работаете?\n",
        "— В логистической компании, координирую поставки.\n\n",
        "— Где вы живёте?\n",
        "— В ",
        Slot("ADDRESS", f"г. {rng.choice(CITIES)}", "e2"),
        ", недавно переехал.\n\n",
        "— Как с вами связаться редакции?\n",
        "— Телефон ",
        Slot("PHONE", _phone(rng), "e3"),
        ", почта ",
        Slot("EMAIL", _email(rng), "e4"),
        ".",
    ]
    text, spans = render_parts(parts)
    return Example(f"ex_{index:04d}", "interview", "interview_intro", text, tuple(spans))


BUILDERS: list = [build_letter, build_document, build_interview]


def build_example(rng: random.Random, index: int) -> Example:
    """Циклически чередует жанры, чтобы малые выборки были сбалансированы."""
    builder = BUILDERS[index % len(BUILDERS)]
    return builder(rng, index)
