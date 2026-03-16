# AGENTS

Этот репозиторий ведется в режиме параллельного внедрения.

## Принципы

1. Один источник правды по статусу: `docs/03_STATUS.md`.
2. Все изменения логируются в `docs/02_WORKLOG.md`.
3. Каждая задача должна иметь владельца-агента и DoD.
4. Не блокировать соседние потоки: работать через четкие контракты API/моделей.
5. Любая спорная архитектурная правка фиксируется в `docs/05_ARCHITECTURE_MVP.md`.

## Агентные потоки

- A1 Platform/Core
- A2 Data Ingestion (MTProto)
- A3 Backend API
- A4 Frontend/UI
- A5 QA/Observability
- A6 DevOps/Security

Подробности: `docs/04_PARALLEL_AGENTS.md`.
