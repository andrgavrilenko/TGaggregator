# 06 Sprint Backlog

## P0 Core

- [ ] PRIORITY #1 (tomorrow): окончательно убрать вложенный вид сообщений в Web UI и подтвердить на пользовательском скриншоте.
- [x] Scaffold проекта и dependency management.
- [x] DB schema + migrations.
- [x] Telegram login/session manager.
- [x] Channels bootstrap + toggle state.
- [x] Incremental ingestion + dedup.
- [x] Feed API.
- [x] Streamlit feed UI (secondary/admin).
- [x] Status endpoint/panel.
- [x] Service autostart templates (`deploy/systemd`).
- [x] Single-writer collector lock.
- [x] Metrics endpoint (`/metrics`).

## P0.1 Telegram-First Transition

- [x] Telegram bot/chat интерфейс как основной UI (minimal).
- [x] Команды чтения ленты (`/latest`).
- [x] Команды управления каналами (`/channels`, `/enable`, `/disable`, `/mute`, `/unmute`).
- [x] Команда добавления каналов (`/add @channel` / `t.me/...`).
- [ ] Inline buttons для быстрых действий из Telegram.
- [ ] UX audit: все основные сценарии проходят без web UI.

## P1 Next

- [ ] Read/unread state.
- [ ] Дедуп похожих кросспостов.
- [ ] Digest/alerts.
- [ ] Расширенная аналитика по каналам.
- [ ] Персональные Telegram presets/watchlists.
- [ ] API auth layer (если выход за localhost/VPN модель).

## Dependencies

1. DB schema -> ingestion/API.
2. Ingestion -> feed API.
3. Feed API -> Telegram UI + Web UI.
4. Telegram-first UX -> alerts/personalization.
5. QA/ops after P0/P0.1 stabilization.

## Definition of Done (current increment)

- Все P0 задачи закрыты.
- Telegram UI покрывает базовые сценарии read/manage/add.
- Есть runbook запуска.
- Есть status/metrics/logging.
- Smoke + unit tests проходят.
