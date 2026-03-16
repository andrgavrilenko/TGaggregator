# Agent A1 Platform Core

## Mission
Подготовить основу проекта: структура кода, конфиг, БД, миграции.

## Tasks
- Создать пакет `src/tgaggerator`.
- Настроить `settings` и env parsing.
- Реализовать модели БД и миграции.
- Подготовить репозитории доступа к данным.

## Inputs
- `docs/05_ARCHITECTURE_MVP.md`
- `docs/06_SPRINT_BACKLOG.md`

## Outputs
- Рабочая БД схема и миграции.
- Документация по запуску локальной БД.

## DoD
- Миграции применяются на чистой базе.
- Базовые CRUD операции проходят smoke test.
