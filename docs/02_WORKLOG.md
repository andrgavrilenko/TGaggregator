# 02 Worklog

## 2026-03-16

- Инициализирован проектный контур в `C:\Users\andrg\coding-projects\tgaggerator`.
- Созданы управляющие документы:
  - `README.md`
  - `AGENTS.md`
  - `docs/01_ROADMAP.md`
  - `docs/02_WORKLOG.md`
  - `docs/03_STATUS.md`
  - `docs/04_PARALLEL_AGENTS.md`
  - `docs/05_ARCHITECTURE_MVP.md`
  - `docs/06_SPRINT_BACKLOG.md`
- Зафиксирована модель параллельного внедрения по 6 агентам.
- Зафиксированы MVP-критерии приемки.

## Шаблон записи

- Дата:
- Агент:
- Задача:
- Изменения:
- Риски/блокеры:
- Следующий шаг:

## 2026-03-16 (update 2)

- Создан каталог `agents/` с 6 карточками потоков:
  - `A1_PLATFORM_CORE.md`
  - `A2_DATA_INGESTION.md`
  - `A3_BACKEND_API.md`
  - `A4_FRONTEND_UI.md`
  - `A5_QA_OBSERVABILITY.md`
  - `A6_DEVOPS_SECURITY.md`
- Добавлен `agents/HANDOFF_TEMPLATE.md` для стандартизированных передач задач между потоками.

## 2026-03-16 (update 3)

- Создан рабочий кодовый scaffold проекта:
  - `pyproject.toml`, `.gitignore`, `.env.example`
  - `src/tgaggerator/*` (config, models, db, repository, init_db)
  - `src/tgaggerator/ingest/*` (gateway + DTO)
  - `src/tgaggerator/cli.py`
  - `src/tgaggerator/api/app.py`
  - `src/tgaggerator/ui/app.py`
  - `scripts/run_api.py`
- Реализованы команды CLI:
  - `init-db`, `login`, `sync-channels`, `bootstrap`, `ingest-once`, `ingest-loop`
- Поднят минимальный API (`/health`, `/status`, `/feed`) и Streamlit UI ленты.
- Добавлены базовые тесты `tests/test_api.py`, `tests/test_repository.py`.
- Верификация:
  - `uv run pytest -q` -> `2 passed`
  - `uv run python -m tgaggerator.cli --help` -> команды доступны.

## 2026-03-16 (update 4)

- Исправлен build-blocker: `pyproject.toml` пересохранен без BOM.
- Исправлена логика dedup в транзакции: `autoflush=True` для SQLAlchemy session.

## 2026-03-16 (update 5)

- Реализована устойчивость ingestion:
  - retry/backoff (`INGEST_MAX_RETRIES`, `INGEST_RETRY_BASE_SEC`, `INGEST_RETRY_MAX_SEC`)
  - отдельная обработка `FloodWaitError` с ожиданием.
- Расширен API:
  - `GET /channels`
  - `PATCH /channels/{channel_id}` для `enabled/muted`.
- Расширен repository слой:
  - `list_channels`, `set_channel_flags`.
- UI обновлен:
  - фильтрация ленты по выбранным каналам.
- Внедрен Alembic:
  - `alembic.ini`
  - `migrations/env.py`
  - `migrations/versions/0001_init.py`
  - `init-db` переключен на `upgrade head`.
- Добавлены тесты:
  - `test_set_channel_flags`
  - `test_channels_patch`
- Верификация:
  - `uv run pytest -q` -> `4 passed`
  - `uv run python -m tgaggerator.cli init-db` -> успешно.
