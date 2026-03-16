# 04 Parallel Agents

## Цель

Разбить внедрение на параллельные независимые потоки с минимальными точками блокировки.

## A1 Platform/Core

- Scope:
  - Структура проекта, shared settings, модели данных.
  - Миграции и базовые utilities.
- Deliverables:
  - `src/tgaggerator/config.py`
  - `src/tgaggerator/db/*`
- DoD:
  - Приложение стартует, миграции проходят в чистой БД.

## A2 Data Ingestion (MTProto)

- Scope:
  - Login/session lifecycle, channel sync, message ingestion.
  - Retry policy, floodwait handling.
- Deliverables:
  - `src/tgaggerator/ingest/*`
  - CLI команды `login`, `sync-channels`, `ingest-*`
- DoD:
  - Инкрементальный синк без дублей.

## A3 Backend API

- Scope:
  - Endpoints: `/feed`, `/status`, `/channels/*`.
  - Query/filter/pagination contract.
- Deliverables:
  - `src/tgaggerator/api/*`
- DoD:
  - API покрывает UI use-cases, swagger актуален.

## A4 Frontend/UI

- Scope:
  - Streamlit интерфейс единой ленты.
  - Фильтры/поиск/пагинация.
- Deliverables:
  - `src/tgaggerator/ui/app.py`
- DoD:
  - Пользователь получает рабочую объединенную ленту.

## A5 QA/Observability

- Scope:
  - Тесты ядра ingestion/API.
  - Логи, статус, базовые метрики.
- Deliverables:
  - `tests/*`, `status` панель
- DoD:
  - Критические сценарии покрыты, ошибки диагностируются.

## A6 DevOps/Security

- Scope:
  - Systemd/supervisor, backup/restore, секреты.
  - Сетевые и доступные ограничения.
- Deliverables:
  - `deploy/*`, runbook
- DoD:
  - Стабильный автозапуск и безопасное хранение секретов.

## Правила параллельной работы

1. Контракты API и DB freeze перед активной разработкой.
2. Любой breaking change отмечать в worklog и status.
3. Merge порядок: A1 -> A2/A3 -> A4 -> A5/A6.
