# 01 Roadmap

Дата старта: 2026-03-16
Текущий релизный вектор: Telegram-first (minimal Telegram UI + web admin UI).

## Product Decisions (accepted)

1. Security: localhost/VPN deployment model for now (no embedded API auth yet).
2. `muted=true` excludes channel from ingestion.
3. Single-writer enforcement is mandatory.
4. Entity map is loaded once per collector process and refreshed on demand.
5. `sync_runs` stays in schema, full usage deferred.
6. Broad exception strategy remains for current speed.
7. Backlog/Status must stay synchronized.
8. Release mode: minimal Telegram UI + web UI in parallel.

## Phase 1 Core Foundation

- Python project structure.
- Environment config.
- DB schema and migrations.
- Data/API contracts.

Status: done.

## Phase 2 Ingestion Stability

- MTProto authorization.
- Bootstrap + incremental sync.
- Retry/backoff/FloodWait.
- Single-writer lock.
- Entity map refresh strategy.

Status: done.

## Phase 3 API + Web Admin UI

- Feed/status/channels API.
- Batch channels update.
- Metrics endpoint.
- Streamlit admin UI.

Status: done.

## Phase 4 Telegram-First UX (minimal)

- Telegram bot as primary UX channel.
- Read commands (`/latest`).
- Channel management commands.
- Channel add command.

Status: in progress (minimal layer implemented).

## Phase 5 Hardening

- Inline controls in Telegram.
- UX audit without web UI dependency.
- E2E smoke with sandbox account.
- Deploy automation and operational playbooks.

Status: planned.

## Acceptance Criteria (next milestone)

1. User can read feed in Telegram.
2. User can manage channels in Telegram.
3. User can add channel from Telegram command.
4. Collector remains single-writer.
5. System remains stable after restart.
6. Web UI continues as secondary/admin fallback.
