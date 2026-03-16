# TGaggregator

Unified Telegram feed for public and private channels available to your account.

TGaggregator consolidates messages into one chronological stream with filtering, search, and operational visibility.

## Why This Project

Telegram content is fragmented across many channels. This project solves the workflow problem for analysts, traders, and researchers who need one clean timeline instead of manually scanning multiple feeds.

## Current MVP Capabilities

- Account-level ingestion (private + public channels you can access).
- Single-writer collector model (stable writes, predictable state).
- Incremental sync with state tracking (`last_msg_id`, lag, errors).
- Retry/backoff and FloodWait handling.
- FastAPI backend with feed/status/channels endpoints.
- Streamlit UI for feed browsing and filtering.
- Alembic migrations for schema lifecycle.

## Architecture (MVP)

1. `Collector` (CLI): pulls new messages via Telegram client API.
2. `Database`: channels, messages, ingestion state, sync runs.
3. `API`: exposes feed, status, channel controls.
4. `UI`: unified timeline and filters.

Key design decision: collector remains the only writer to reduce lock/contention risks.

## Repository Structure

```text
src/tgaggerator/
  api/           # FastAPI app
  ingest/        # Telegram gateway + DTOs
  ui/            # Streamlit app
  cli.py         # Operational commands
  models.py      # SQLAlchemy models
  repository.py  # DB queries/commands
  migrations.py  # Alembic launcher
migrations/      # Alembic env + revisions
docs/            # Roadmap, status, runbooks, API docs
scripts/         # Service launchers
tests/           # Unit/API tests
```

## Quick Start

### 1) Prepare environment

```bash
copy .env.example .env
```

Fill required values in `.env`:
- `TG_API_ID`
- `TG_API_HASH`
- `TG_PHONE`

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

### 5) Sync channels and bootstrap history

```bash
uv run python -m tgaggerator.cli sync-channels
uv run python -m tgaggerator.cli bootstrap --limit 200
```

### 6) Start collector loop

```bash
uv run python -m tgaggerator.cli ingest-loop --interval 30
```

### 7) Start API and UI

```bash
uv run python scripts/run_api.py
uv run streamlit run src/tgaggerator/ui/app.py
```

Open:
- API docs: `http://127.0.0.1:8000/docs`
- UI: `http://127.0.0.1:8501`

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `TG_API_ID` | Yes | - | Telegram app id |
| `TG_API_HASH` | Yes | - | Telegram app hash |
| `TG_PHONE` | For first login | - | Phone for auth |
| `TG_SESSION_PATH` | No | `.secrets/tg_session` | Session file path |
| `DB_URL` | No | `sqlite:///./data/tgaggerator.db` | Database DSN |
| `API_HOST` | No | `127.0.0.1` | API bind host |
| `API_PORT` | No | `8000` | API port |
| `UI_API_BASE` | No | `http://127.0.0.1:8000` | UI backend URL |
| `DEFAULT_BOOTSTRAP_LIMIT` | No | `200` | Initial history depth per channel |
| `INGEST_INTERVAL_SEC` | No | `30` | Collector loop interval |
| `INGEST_MAX_RETRIES` | No | `3` | Retry attempts |
| `INGEST_RETRY_BASE_SEC` | No | `2` | Exponential backoff base |
| `INGEST_RETRY_MAX_SEC` | No | `30` | Backoff cap |

## API Overview

- `GET /health`
- `GET /status`
- `GET /channels`
- `PATCH /channels/{channel_id}`
- `GET /feed`

Detailed reference: [docs/08_API_REFERENCE.md](docs/08_API_REFERENCE.md)

## Quality Gates

```bash
uv run pytest -q
```

## Security Notes

- Never commit `.env` or `.session` files.
- Treat Telegram session as account secret.
- Restrict UI/API exposure on public hosts.

See: [SECURITY.md](SECURITY.md)

## Documentation

- Project roadmap: [docs/01_ROADMAP.md](docs/01_ROADMAP.md)
- Worklog: [docs/02_WORKLOG.md](docs/02_WORKLOG.md)
- Live status: [docs/03_STATUS.md](docs/03_STATUS.md)
- Architecture: [docs/05_ARCHITECTURE_MVP.md](docs/05_ARCHITECTURE_MVP.md)
- Deploy runbook: [docs/07_DEPLOY_RUNBOOK.md](docs/07_DEPLOY_RUNBOOK.md)

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).