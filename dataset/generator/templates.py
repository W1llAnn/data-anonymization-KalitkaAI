"""Шаблоны трёх жанров: письма, документы, фрагменты интервью.

Каждый шаблон — функция, собирающая текст из частей (строки и Slot).
Границы спанов и повторные упоминания (одинаковый entity_id) отслеживает render.

Ловушки (по ТЗ «похожие на контакты артефакты», «неоднозначные числа») — обычные
строки без Slot:热线ы вида 8-800-XXX-XX-XX, логины вида ivan.petrov-2024,
номера заказов и суммы остаются в тексте неразмеченными.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from dataset.generator.pii_gen import (
    generate_account,
    generate_card,
    generate_inn10,
    generate_inn12,
    generate_passport,
    generate_snils,
)
from dataset.generator.pools import CITIES, DOMAINS, EMAIL_LOCALS, NAME_FORMS, STREETS
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


def build_letter(rng: random.Random, index: int) -> Example:
    person = rng.choice(NAME_FORMS)
    variant = rng.random()
    parts: list[str | Slot]
    template: str

    if variant < 0.15:
        # Без ПДн (обязательная категория ТЗ)
        parts = [
            "Здравствуйте!\n\n",
            f"Направляю отчёт по договору №{rng.randint(100, 999)} на согласование. ",
            f"Жду замечаний до {rng.randint(10, 28)}.11.2026.\n\n",
            "С уважением,\nОтдел делопроизводства",
        ]
        template = "letter_plain"
    elif variant < 0.5:
        # Напоминание: имя в двух падежах, сумма и срок — неоднозначные числа,
        # «горячая линия 8-800-XXX-XX-XX» — ловушка, похожая на контакт
        parts = [
            "Добрый день, ",
            Slot("PERSON", person["dat"], "e1"),
            "!\n\n",
            f"Напоминаем про оплату {rng.randint(50, 900)} 000 руб. ",
            f"по счёту №{rng.randint(1000, 9999)}. ",
            "Крайний срок — 20-е число. Вопросы — на горячую линию 8-800-XXX-XX-XX.\n\n",
            "С уважением, служба поддержки",
        ]
        template = "letter_reminder"
    elif variant < 0.65:
        # Служебный тикет: логин-идентификатор и номер тикета — ловушки
        parts = [
            "Тикет №",
            str(rng.randint(10000, 99999)),
            "\nЗаявитель: ",
            Slot("PERSON", person["nom"], "e1"),
            f" (логин {rng.choice(EMAIL_LOCALS)}-{rng.randint(2019, 2026)}).\n",
            "Проблема: не пришло уведомление на ",
            Slot("EMAIL", _email(rng), "e2"),
            ".\nКонтактный телефон: ",
            Slot("PHONE", _phone(rng), "e3"),
            ".",
        ]
        template = "letter_ticket"
    elif variant < 0.85:
        # Реквизиты оплаты: карта (Лун) и расчётный счёт; номер договора — ловушка
        card = generate_card(rng, grouped=rng.random() < 0.7)
        parts = [
            "Здравствуйте, ",
            Slot("PERSON", person["dat"], "e1"),
            "!\n\n",
            f"Оплата по договору №{rng.randint(100, 999)}: ",
            "карта ",
            Slot("DOC_ID", card, "e2"),
            " (получатель — ",
            Slot("PERSON", person["nom"], "e1"),
            "), расчётный счёт ",
            Slot("DOC_ID", generate_account(rng), "e3"),
            ", банк «Столичный».\n\n",
            "После оплаты пришлите чек на ",
            Slot("EMAIL", _email(rng), "e4"),
            ".",
        ]
        template = "letter_requisites"
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
    parts: list[str | Slot]
    template: str

    if rng.random() < 0.5:
        # Справка: паспорт или СНИЛС (валидная контрольная сумма), адрес, контакты
        doc = generate_passport(rng) if rng.random() < 0.5 else generate_snils(rng)
        parts = [
            "СПРАВКА\n\n",
            "Дана ",
            Slot("PERSON", person["dat"], "e1"),
            ", документ ",
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
        template = "document_cert"
    else:
        # Заявление: валидный ИНН (10 или 12 цифр) + адрес; номер дела — ловушка
        inn = generate_inn10(rng) if rng.random() < 0.5 else generate_inn12(rng)
        parts = [
            "ЗАЯВЛЕНИЕ\n\n",
            "Заявитель: ",
            Slot("PERSON", person["nom"], "e1"),
            ", ИНН ",
            Slot("DOC_ID", inn, "e2"),
            ", адрес регистрации: ",
            Slot("ADDRESS", _address(rng), "e3"),
            ".\n\n",
            f"Прошу рассмотреть обращение по делу №{rng.randint(100000, 999999)}.\n",
            "Ответ направить на ",
            Slot("EMAIL", _email(rng), "e4"),
            ".",
        ]
        template = "document_application"

    text, spans = render_parts(parts)
    return Example(f"ex_{index:04d}", "document", template, text, tuple(spans))


def build_interview(rng: random.Random, index: int) -> Example:
    person = rng.choice(NAME_FORMS)
    parts: list[str | Slot]
    template: str

    if rng.random() < 0.6:
        parts = [
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
        template = "interview_intro"
    else:
        # Рыхлый адрес (только улица) — сложный случай для детекции
        parts = [
            "Беседовал корреспондент с ",
            Slot("PERSON", person["acc"], "e1"),
            ".\n\n",
            "— Как добираетесь на работу?\n",
            f"— Живу на улице {rng.choice(STREETS)}, рядом с парком, до офиса пешком.\n\n",
            "— Как читатели могут вам написать?\n",
            "— На почту ",
            Slot("EMAIL", _email(rng), "e2"),
            ", отвечаю сам. Телефон для срочных вопросов: ",
            Slot("PHONE", _phone(rng), "e3"),
            ".",
        ]
        template = "interview_loose"

    text, spans = render_parts(parts)
    return Example(f"ex_{index:04d}", "interview", template, text, tuple(spans))


BUILDERS: list = [build_letter, build_document, build_interview]


def build_example(rng: random.Random, index: int) -> Example:
    """Циклически чередует жанры, чтобы малые выборки были сбалансированы."""
    builder = BUILDERS[index % len(BUILDERS)]
    return builder(rng, index)
