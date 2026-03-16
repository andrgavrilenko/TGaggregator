# 03 Status

Обновлено: 2026-03-16

## Сделано

- [x] Базовый scaffold проекта и зависимости.
- [x] Схема БД + Alembic migrations.
- [x] CLI: `login`, `sync-channels`, `bootstrap`, `ingest-once`, `ingest-loop`, `add-channel`.
- [x] Ingestion: incremental sync + dedup + retry/backoff + FloodWait.
- [x] Single-writer enforcement через `collector` lock.
- [x] Entity-map стратегия: preload per process + refresh on missing entity.
- [x] API: `/health`, `/status`, `/metrics`, `/channels`, `/feed`.
- [x] API: single/batch channel updates.
- [x] Streamlit web UI (secondary/admin).
- [x] Telegram UI (minimal primary): `/latest`, `/channels`, `/enable`, `/disable`, `/mute`, `/unmute`, `/add`.
- [x] One-command stack lifecycle in CLI: `up` / `down` (collector + api + ui [+bot]).
- [x] No-terminal setup in Web UI via `/ops/*` endpoints (init/login/sync/bootstrap/ingest).
- [x] One-click start in Web UI: `Пуск` (`/ops/start`) + optional auto-start on page load.
- [x] Public-only mode without Telegram user auth (add `@username` channels + ingest from web view).
- [x] Feed UX cleanup: messages shown expanded by default (no per-item nested collapse).
- [x] Deploy artifacts: systemd unit templates + install script.
- [x] Smoke-check script.
- [x] Тесты проходят.
- [x] Конфиг устойчив к пустым optional env (`env_ignore_empty=True`).

## Принятые продуктовые решения

- [x] Security model: localhost/VPN (без встроенного API auth на текущем этапе).
- [x] `muted=true` исключает канал из ingestion.
- [x] `sync_runs` оставлен в схеме, полная эксплуатация позже.
- [x] Telegram-first UX + web admin fallback.

## В работе

- [ ] PRIORITY #1 (next session): проблема вложенности сообщений в UI не считается закрытой, нужна финальная фиксация и верификация по экрану пользователя.
- [ ] Inline controls в Telegram UI.
- [ ] UX audit сценариев без web UI.
- [ ] E2E smoke с реальным sandbox аккаунтом.
- [ ] Public parser hardening (fallback selectors + parser watchdog).

## Прогресс

- Project management/docs: 100%
- Core implementation: 80%
- Общий прогресс MVP+: 86%
