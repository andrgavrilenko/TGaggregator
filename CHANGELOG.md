# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Added

- Batch channel flags update endpoint: `PATCH /channels`.
- Metrics endpoint: `GET /metrics` (Prometheus-style text format).
- Structured collector event logs with `LOG_LEVEL` setting.
- Safer message permalink builder for public and private channels.
- Single-writer collector lock (`COLLECTOR_LOCK_PATH`).
- Process-level entity cache with refresh-on-missing strategy.
- CLI command: `add-channel`.
- Minimal Telegram primary UI module and runner (`scripts/run_telegram_ui.py`).
- systemd template for telegram-ui service.
- Smoke-check script (`scripts/smoke_check.py`).
- Additional tests for API/repository/locking semantics.
- Stack orchestration commands in CLI:
  - `up` (start collector + api + ui, optional bot)
  - `down` (stop stack from PID state file)
- PID-state persistence for stack lifecycle (`data/runtime/stack_pids.json`).
- API operations endpoints for no-terminal onboarding:
  - `/ops/status`, `/ops/init-db`
  - `/ops/login/request-code`, `/ops/login/confirm`
  - `/ops/sync-channels`, `/ops/bootstrap`, `/ops/ingest-once`
- One-click startup endpoint and UI trigger:
  - `POST /ops/start` (init + auth-check + sync + bootstrap + ingest)
  - primary `Пуск` button in web UI
  - optional `Auto-start on page load` toggle
- Public-only mode (no user Telegram auth):
  - public channel ingestion from `https://t.me/s/<username>`
  - `POST /ops/public/add` for adding public channels from UI
  - fallback to public mode in `/ops/start`, `/ops/sync-channels`, `/ops/bootstrap`, `/ops/ingest-once`

### Changed

- Product policy fixed: `muted=true` excludes channel from ingestion.
- Product policy fixed: no embedded API auth yet; localhost/VPN deployment model.
- Documentation synchronized with implemented scope.
- Settings loader now ignores empty env values (fixes startup crash on empty optional ints).

## [0.1.0] - 2026-03-16

### Added

- Initial MVP scaffold for TGaggregator.
- Telegram ingestion CLI (`login`, `sync-channels`, `bootstrap`, `ingest-*`).
- Retry/backoff and FloodWait handling.
- FastAPI endpoints (`/health`, `/status`, `/channels`, `/feed`).
- Streamlit feed UI.
- SQLAlchemy models and repository layer.
- Alembic migrations (`0001_init`).
- Base tests for API and repository.
- Project documentation package (roadmap, status, architecture, runbook, API reference).
