# TGaggregator

Unified Telegram feed for public and private channels available to your account.

TGaggregator consolidates messages into one chronological stream and exposes the feed both in Telegram (primary UI) and web (secondary/admin UI).

## Product Direction

- Primary UI: Telegram bot commands.
- Secondary UI: Streamlit web panel.
- API is intended for localhost/VPN deployment without built-in auth (current stage).

## Current Capabilities

- Account-level ingestion (private + public channels you can access).
- Single-writer collector lock (`COLLECTOR_LOCK_PATH`) to prevent parallel collectors.
- Incremental sync with state tracking (`last_msg_id`, lag, errors).
- Retry/backoff + FloodWait handling.
- Structured collector logs (JSON events).
- FastAPI endpoints: feed/status/channels/metrics.
- Telegram UI bot commands for read/manage/add workflows.
- Streamlit UI for admin/diagnostic browsing.
- Alembic migrations for schema lifecycle.

## Important Semantics

- `muted=true` means channel is excluded from ingestion (not only hidden in UI).
- Write/API security is environment-level (localhost/VPN/reverse proxy), not API-key level yet.

## Repository Structure

```text
src/tgaggerator/
  api/            # FastAPI app
  ingest/         # Telegram gateway, DTOs, collector lock
  ui/             # Streamlit app
  telegram_ui.py  # Telegram bot primary UI
  cli.py          # Operational commands
  models.py       # SQLAlchemy models
  repository.py   # DB queries/commands
  migrations.py   # Alembic launcher
migrations/       # Alembic env + revisions
deploy/systemd/   # systemd service templates
docs/             # Roadmap, status, runbooks, API docs
scripts/          # Service launchers + smoke check
tests/            # Unit/API tests
```

## Quick Start

### 1) Prepare environment

```bash
copy .env.example .env
```

Required values:
- `TG_API_ID`
- `TG_API_HASH`
- `TG_PHONE`

For Telegram bot UI:
- `TG_BOT_TOKEN`
- optional `TG_BOT_ALLOWED_CHAT_ID`

### 2) Install dependencies

```bash
uv sync
```

### 3) Initialize database

```bash
uv run python -m tgaggerator.cli init-db
```

### 4) Authorize Telegram account

```bash
uv run python -m tgaggerator.cli login
```

### 5) Sync and bootstrap

```bash
uv run python -m tgaggerator.cli sync-channels
uv run python -m tgaggerator.cli bootstrap --limit 200
```

### 6) Start services

```bash
uv run python -m tgaggerator.cli ingest-loop --interval 30
uv run python scripts/run_api.py
uv run streamlit run src/tgaggerator/ui/app.py
uv run python scripts/run_telegram_ui.py
```

Open:
- API docs: `http://127.0.0.1:8000/docs`
- Web UI: `http://127.0.0.1:8501`

## Telegram UI Commands

- `/start`
- `/latest [N]`
- `/channels`
- `/enable <id>` / `/disable <id>`
- `/mute <id>` / `/unmute <id>`
- `/add <@channel or https://t.me/...>`

## CLI Commands

```bash
uv run python -m tgaggerator.cli --help
```

Includes:
- `init-db`, `login`, `sync-channels`, `add-channel`
- `bootstrap`, `ingest-once`, `ingest-loop`

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `TG_API_ID` | Yes | - | Telegram app id |
| `TG_API_HASH` | Yes | - | Telegram app hash |
| `TG_PHONE` | For first login | - | Phone for auth |
| `TG_SESSION_PATH` | No | `.secrets/tg_session` | Session file path |
| `TG_BOT_TOKEN` | For Telegram UI | - | Telegram bot token |
| `TG_BOT_ALLOWED_CHAT_ID` | No | - | Restrict bot commands to one chat |
| `DB_URL` | No | `sqlite:///./data/tgaggerator.db` | Database DSN |
| `API_HOST` | No | `127.0.0.1` | API bind host |
| `API_PORT` | No | `8000` | API port |
| `UI_API_BASE` | No | `http://127.0.0.1:8000` | API base for web/bot clients |
| `DEFAULT_BOOTSTRAP_LIMIT` | No | `200` | Initial history depth per channel |
| `INGEST_INTERVAL_SEC` | No | `30` | Collector loop interval |
| `INGEST_MAX_RETRIES` | No | `3` | Retry attempts |
| `INGEST_RETRY_BASE_SEC` | No | `2` | Exponential backoff base |
| `INGEST_RETRY_MAX_SEC` | No | `30` | Backoff cap |
| `COLLECTOR_LOCK_PATH` | No | `.secrets/collector.lock` | Single-writer lock file |
| `LOG_LEVEL` | No | `INFO` | Collector/API log verbosity |

## API Overview

- `GET /health`
- `GET /status`
- `GET /metrics`
- `GET /channels`
- `PATCH /channels/{channel_id}`
- `PATCH /channels` (batch update)
- `GET /feed`

Detailed reference: [docs/08_API_REFERENCE.md](docs/08_API_REFERENCE.md)

## Quality Gates

```bash
uv run pytest -q
uv run python scripts/smoke_check.py
```

## Security Notes

- Never commit `.env` or `.session` files.
- Treat Telegram session as account secret.
- Keep API/UI local or behind VPN/reverse proxy auth.

See: [SECURITY.md](SECURITY.md)

## Documentation

- Roadmap: [docs/01_ROADMAP.md](docs/01_ROADMAP.md)
- Worklog: [docs/02_WORKLOG.md](docs/02_WORKLOG.md)
- Status: [docs/03_STATUS.md](docs/03_STATUS.md)
- Architecture: [docs/05_ARCHITECTURE_MVP.md](docs/05_ARCHITECTURE_MVP.md)
- Deploy runbook: [docs/07_DEPLOY_RUNBOOK.md](docs/07_DEPLOY_RUNBOOK.md)

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).