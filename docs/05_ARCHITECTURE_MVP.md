# 05 Architecture MVP

## Interface Policy

- Primary UI: Telegram bot/chat UX.
- Secondary UI: Streamlit (operator/diagnostic console).

## Security Policy (current stage)

- API authentication is not embedded yet.
- Deployment model: localhost/VPN/reverse-proxy protected access.
- Write endpoints must not be exposed publicly without network-level controls.

## Components

1. Collector (single writer)
- Pulls Telegram messages.
- Persists into DB and updates ingestion state.
- Enforced by file lock (`COLLECTOR_LOCK_PATH`).

2. Database
- PostgreSQL preferred (SQLite acceptable for local start).
- Tables: `channels`, `messages`, `ingestion_state`, `sync_runs`.

3. API Service
- Exposes feed/status/metrics.
- Manages channel flags (`enabled`, `muted`) and batch updates.

4. Telegram UI (Primary)
- Commands for reading feed and channel management.
- Commands for adding channels by handle/link.

5. Web UI (Secondary)
- Streamlit feed view and filters.
- Used as fallback/admin console.

## Domain Semantics

- `enabled=false` -> channel excluded from ingestion.
- `muted=true` -> channel excluded from ingestion (chosen policy).
- Message dedup key: (`channel_id`, `tg_message_id`).

## Anti-Bottleneck Decisions

- Single writer to avoid DB write contention.
- Incremental sync by `last_msg_id`.
- Entity map loaded once per process and refreshed on missing entity.
- Retry/backoff for rate-limits.
- UI layers do not write DB directly; they use API/commands.

## Non-Functional Requirements

- Restart resilience.
- Transparent diagnostics (status + structured logs + metrics).
- Secret/session protection.
- Telegram-first UX without blocking web-admin flows.
