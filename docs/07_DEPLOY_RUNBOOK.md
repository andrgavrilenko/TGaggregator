# 07 Deploy Runbook (MVP)

## Objective

Run TGaggregator on a VPS in a stable and recoverable way.

## Recommended Services

1. `collector` (long-running ingestion loop)
2. `api` (FastAPI service)
3. `ui` (Streamlit service)

## Preconditions

- Linux host with Python 3.11+
- Reverse proxy (Nginx/Caddy) if public access is required
- Firewall configured

## Setup

```bash
git clone <repo>
cd TGaggregator
cp .env.example .env
# fill secrets
uv sync
uv run python -m tgaggerator.cli init-db
```

## Initial data load

```bash
uv run python -m tgaggerator.cli login
uv run python -m tgaggerator.cli sync-channels
uv run python -m tgaggerator.cli bootstrap --limit 200
```

## Runtime commands

```bash
uv run python -m tgaggerator.cli ingest-loop --interval 30
uv run python scripts/run_api.py
uv run streamlit run src/tgaggerator/ui/app.py --server.port 8501 --server.address 127.0.0.1
```

## Health checks

- API: `GET /health`
- API docs: `/docs`
- UI reachable on configured host/port

## Backup policy

- Daily DB backup.
- Exclude `.session` from backup transfers unless encrypted.
- Keep at least 7 recent backups.

## Incident quick actions

1. Check logs for collector/API/UI processes.
2. Validate DB file/connection.
3. Restart failed service only, not full stack.
4. If Telegram auth broke: run `login` again.