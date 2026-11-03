"""Генерация синтетических ПДн с валидными контрольными суммами.

Детекторы Р2 находят ИНН/СНИЛС только при корректной контрольной сумме,
поэтому датасет обязан содержать валидные номера (иначе разметка станет
недостижимой для правил). Логика сумм — как в anongw.anonymizer.rules.
"""

from __future__ import annotations

import random

_INN10_W = (2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN12_W1 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN12_W2 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)


def _inn10_control(digits: list[int]) -> int:
    """Контрольная цифра ИНН-10 по первым девяти цифрам."""
    return sum(d * w for d, w in zip(digits, _INN10_W, strict=True)) % 11 % 10


def _inn12_c1(digits: list[int]) -> int:
    """Первая контрольная ИНН-12 по первым десяти цифрам."""
    return sum(d * w for d, w in zip(digits, _INN12_W1, strict=True)) % 11 % 10


def _inn12_c2(digits: list[int]) -> int:
    """Вторая контрольная ИНН-12 по первым одиннадцати цифрам."""
    return sum(d * w for d, w in zip(digits, _INN12_W2, strict=True)) % 11 % 10


def generate_inn10(rng: random.Random) -> str:
    digits = [rng.randint(1, 9)] + [rng.randint(0, 9) for _ in range(8)]
    digits.append(_inn10_control(digits))
    return "".join(map(str, digits))


def generate_inn12(rng: random.Random) -> str:
    digits = [rng.randint(1, 9)] + [rng.randint(0, 9) for _ in range(9)]
    digits.append(_inn12_c1(digits))
    digits.append(_inn12_c2(digits))
    return "".join(map(str, digits))


def generate_snils(rng: random.Random) -> str:
    digits = [rng.randint(0, 9) for _ in range(9)]
    control = sum(d * (9 - i) for i, d in enumerate(digits)) % 101
    if control == 100:
        control = 0
    body = "".join(map(str, digits))
    return f"{body[0:3]}-{body[3:6]}-{body[6:9]} {control:02d}"


def generate_passport(rng: random.Random) -> str:
    return f"{rng.randint(1000, 9999)} {rng.randint(100000, 999999)}"


def _luhn_total(digits: list[int]) -> int:
    total = 0
    for position, digit in enumerate(reversed(digits)):
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total


def generate_card(rng: random.Random, grouped: bool = True) -> str:
    """Номер карты (16 цифр, Лун-валидный): 4111 1111 1111 1111 или слитно."""
    digits = [4] + [rng.randint(0, 9) for _ in range(14)]
    digits.append((10 - _luhn_total(digits + [0]) % 10) % 10)
    body = "".join(map(str, digits))
    if grouped:
        return " ".join(body[i : i + 4] for i in range(0, 16, 4))
    return body


def generate_account(rng: random.Random) -> str:
    """Расчётный счёт: 20 цифр с реалистичным префиксом 40817."""
    tail = "".join(str(rng.randint(0, 9)) for _ in range(15))
    return f"40817{tail}"
