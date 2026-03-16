# 07 Deploy Runbook (MVP)

## Objective

Run TGaggregator on VPS with stable ingestion and Telegram-first access.

## Services

1. `collector` (ingestion loop, single writer)
2. `api` (FastAPI)
3. `ui` (Streamlit admin)
4. `telegram-ui` (Telegram bot commands)

## Preconditions

- Linux host with Python 3.11+
- Reverse proxy/VPN policy for restricted access
- Firewall configured

## Setup

```bash
git clone <repo>
cd TGaggregator
cp .env.example .env
# fill secrets (TG_API_*, TG_BOT_TOKEN)
uv sync
uv run python -m tgaggerator.cli init-db
```

## Initial data load

```bash
uv run python -m tgaggerator.cli login
uv run python -m tgaggerator.cli sync-channels
uv run python -m tgaggerator.cli bootstrap --limit 200
```

## Runtime (manual)

```bash
uv run python -m tgaggerator.cli ingest-loop --interval 30
uv run python scripts/run_api.py
uv run streamlit run src/tgaggerator/ui/app.py --server.port 8501 --server.address 127.0.0.1
uv run python scripts/run_telegram_ui.py
```

## Runtime (systemd)

Artifacts:
- `deploy/systemd/tgaggerator-api.service`
- `deploy/systemd/tgaggerator-collector.service`
- `deploy/systemd/tgaggerator-ui.service`
- `deploy/systemd/tgaggerator-telegram-ui.service`

Install:

```bash
sudo bash deploy/systemd/install.sh
sudo systemctl start tgaggerator-api tgaggerator-collector tgaggerator-ui tgaggerator-telegram-ui
```

## Health checks

- API health: `/health`
- API metrics: `/metrics`
- API docs: `/docs`
- UI reachable on configured host/port
- Telegram bot responds to `/start`

Smoke check:

```bash
uv run python scripts/smoke_check.py
```

## Backup policy

- Daily DB backup.
- Do not export `.session` unencrypted.
- Keep at least 7 recent backups.

## Incident quick actions

1. Check collector/API/UI/bot logs.
2. Validate DB path/connectivity.
3. Ensure only one collector instance is active (lock file + process check).
4. If Telegram auth/session broke: run `login` again.
