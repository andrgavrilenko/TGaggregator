# 05 Architecture MVP

## Компоненты

1. Collector (single writer)
- Забирает сообщения из Telegram.
- Пишет в БД и обновляет ingestion state.

2. Database
- PostgreSQL (предпочтительно) или SQLite для локального старта.
- Таблицы: channels/messages/ingestion_state/sync_runs.

3. API Service
- Отдает ленту и статус.
- Управляет включением/выключением каналов.

4. UI (Streamlit)
- Рендерит единую ленту.
- Фильтры: канал, период, media, текстовый поиск.

## Анти-бутылочные решения

- Single writer для предотвращения lock contention.
- Инкрементальный синк по `last_msg_id`.
- Кэш entity resolution (не резолвить username в цикле).
- Retry/backoff для rate-limit.

## Нефункциональные требования

- Устойчивость после рестартов.
- Прозрачная диагностика ошибок.
- Защита session/secrets.
