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

## 2026-03-16 (update 6)

- Выполнен профессиональный docs-pack для GitHub:
  - Полностью переработан `README.md` (позиционирование, архитектура, quick start, env, API).
  - Добавлены `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`.
  - Добавлены `docs/07_DEPLOY_RUNBOOK.md` и `docs/08_API_REFERENCE.md`.
  - Добавлены шаблоны `.github`:
    - `ISSUE_TEMPLATE/bug_report.md`
    - `ISSUE_TEMPLATE/feature_request.md`
    - `PULL_REQUEST_TEMPLATE.md`
- Обновлен `.gitignore`: исключены runtime-логи (`logs/`).
- Верификация после изменений: `uv run pytest -q` -> `4 passed`.

## 2026-03-16 (update 7)

- Добавлен batch-эндпоинт управления каналами:
  - `PATCH /channels` с телом `{ channel_ids, enabled?, muted? }`.
- Расширен repository слой:
  - `set_channels_flags`.
- Улучшена генерация ссылок сообщений:
  - публичные каналы: `https://t.me/{username}/{id}`
  - private fallback: `https://t.me/c/{internal_id}/{id}`.
- Добавлено структурированное логирование collector-а:
  - события `ingest_tick_ok/failed`, `channel_ingest_ok/retry/floodwait/failed`, `channel_entity_missing`.
- Добавлена настройка `LOG_LEVEL` в конфиг и `.env.example`.
- Тесты расширены:
  - batch update repository/api
  - проверка link builder.
- Обновлены `README.md` и `docs/08_API_REFERENCE.md`.
- Верификация: `uv run pytest -q` -> `7 passed`.

## 2026-03-16 (update 8)

- Обновлен продуктовый вектор в roadmap: Telegram назначен primary UI channel.
- В `docs/01_ROADMAP.md` добавлена фаза `Telegram-First UX` с конкретными Telegram-сценариями:
  - чтение ленты,
  - управление каналами,
  - добавление каналов.
- В `docs/05_ARCHITECTURE_MVP.md` закреплена архитектурная модель:
  - Telegram UI = primary,
  - Streamlit UI = secondary/admin.
- В `docs/06_SPRINT_BACKLOG.md` добавлен отдельный блок `P0.1 Telegram-First Transition`.

## 2026-03-16 (update 9)

- Применены пользовательские решения по quiz:
  - security: localhost/VPN model,
  - muted = stop ingestion,
  - single-writer lock enabled,
  - entity preload + refresh on miss,
  - sync_runs deferred,
  - broad catch strategy retained,
  - docs backlog/status synchronized,
  - release mode: minimal Telegram UI + web.
- Реализован `collector` lock (`COLLECTOR_LOCK_PATH`).
- CLI ingestion переведен на process-level entity cache + refresh on missing entity.
- Добавлена команда `add-channel` в CLI.
- Добавлен Telegram UI модуль и runner:
  - `src/tgaggerator/telegram_ui.py`
  - `scripts/run_telegram_ui.py`
- Добавлены deploy units для telegram-ui.
- Обновлены `README`, `roadmap`, `architecture`, `sprint backlog`, `runbook`, `api reference`.
- Добавлены тесты:
  - `tests/test_lock.py`
  - проверка muted ingestion policy в `test_repository.py`.

## 2026-03-16 (update 10)

- Переключен активный рабочий контур обратно на `tgaggerator`.
- Исправлен runtime-блокер API:
  - причина: пустой `TG_BOT_ALLOWED_CHAT_ID=` в `.env` вызывал `ValidationError` при старте.
  - решение: `env_ignore_empty=True` в `SettingsConfigDict` (`src/tgaggerator/config.py`).
- Добавлен regression test:
  - `tests/test_config.py::test_empty_optional_int_env_is_ignored`.
- Верификация:
  - `uv run pytest -q` -> `11 passed`.
  - `GET /health` -> `200`.
  - `scripts/smoke_check.py` -> все проверки `OK`.

## 2026-03-16 (update 11)

- Добавлен встроенный orchestration в CLI:
  - `up` — единый старт collector + API + web UI (+ опционально bot через `--with-bot`).
  - `down` — единая остановка процессов по PID-state.
- Реализован PID-state файл стека:
  - `data/runtime/stack_pids.json`.
- Обновлен `README` (quick start теперь через `up`/`down`).
- Добавлены unit-тесты orchestration-хелперов:
  - `tests/test_cli_stack.py`.

## 2026-03-16 (update 12)

- Реализован no-terminal onboarding внутри продукта:
  - новые API операции `/ops/*` (init-db, login code flow, sync, bootstrap, ingest-once).
  - в Streamlit UI добавлен блок `Setup (без терминала)` с кнопками выполнения шагов.
- Расширен `TelegramGateway` для web-login flow:
  - `request_login_code()`
  - `sign_in_with_code()`
  - `is_authorized()`
- Добавлены API тесты:
  - `tests/test_ops_api.py`.

## 2026-03-16 (update 13)

- Добавлен one-click pipeline:
  - новый endpoint `POST /ops/start` (init-db + auth-check + sync + bootstrap + ingest-once).
  - в Streamlit UI добавлена основная кнопка `Пуск`.
  - добавлен toggle `Auto-start on page load`.
- Сценарий без терминала теперь:
  - открыть UI
  - нажать `Пуск`
  - если неавторизовано — пройти one-time login в том же сайдбаре.
- Расширены тесты ops API (`tests/test_ops_api.py`) для `/ops/start`.

## 2026-03-16 (update 14)

- Добавлен public-only режим без пользовательской Telegram авторизации:
  - новый модуль `ingest/public_web.py` (чтение `https://t.me/s/<username>`).
  - endpoint `POST /ops/public/add` для добавления публичных каналов из UI.
  - fallback публичного режима в `/ops/start`, `/ops/sync-channels`, `/ops/bootstrap`, `/ops/ingest-once`.
- UI `Quick Start` обновлён:
  - поле `Public channel (@username)` + кнопка `Add public channel`.
  - `Пуск` теперь работает и в public-only режиме.
- Добавлена env-переменная `PUBLIC_CHANNELS` (comma-separated) в `.env.example` и `config.py`.
- Верификация: `uv run pytest -q` -> `21 passed`.

## 2026-03-16 (update 15)

- UX cleanup:
  - лента сообщений в UI переведена в открытый режим по умолчанию (без вложенных карточек на каждое сообщение).
  - сохранён только технический expander для JSON-результата операций.
- Ops cleanup:
  - зафиксировано отсутствие runtime-мусора (нет активных stack pid state, фоновые процессы остановлены перед закрытием сессии).
- Session memory сохранена:
  - `docs/09_SESSION_MEMORY_2026-03-16.md`
- Верификация:
  - `uv run pytest -q` -> `22 passed`.

## 2026-03-16 (update 16)

- По запросу пользователя зафиксировано:
  - проблема вложенности сообщений в UI считается НЕ решенной.
  - задача поставлена как `PRIORITY #1` на следующую сессию.
- Обновлены документы:
  - `docs/09_SESSION_MEMORY_2026-03-16.md`
  - `docs/03_STATUS.md`
  - `docs/06_SPRINT_BACKLOG.md`
