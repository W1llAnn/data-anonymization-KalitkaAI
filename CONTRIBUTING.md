# Как работать в репозитории

## Начало работы

```bash
python -m venv .venv
source .venv/Scripts/activate        # Windows (Git Bash); .venv\Scripts\Activate.ps1 в PowerShell
pip install -e ".[dev]"

pytest -q                            # тесты
ruff check src tests                 # линтер
mypy                                 # типы
```

Секреты — только через `.env` (скопировать из `.env.example`); файл в git не попадает.

## Ветки и очерёдность

Полные правила — [docs/git-workflow.md](docs/git-workflow.md). Кратко:

- прямой пуш в `main` запрещён;
- неделя = ветка `week-NN`, роль-ветки `week-NN-rX-тема` мержатся в неё по порядку пушей;
- ветки после мержа не удаляются.

## Ревью

- PR называем `[Неделя N][РX] тема`, шаблон заполнен полностью.
- Мерж — при зелёном CI и одном approvals; изменения `contracts.py` и схем — только с ревью Р1.
- Ревьюер проверяет: соответствие задачам недели, отсутствие ПДн и ключей в коде/логах/тестах.

## Соглашения по коду

- Python 3.12+, типизация обязательна (`mypy --strict`-совместимо в пределах `src/anongw`).
- Формат — `ruff format`; импорты сортирует ruff.
- Компоненты общаются только через контракты `src/anongw/contracts.py`.
