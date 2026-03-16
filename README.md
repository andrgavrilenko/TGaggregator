# tgaggerator

Telegram aggregator with one chronological feed across channels (public + private channels available to your account).

## Implemented now

- Single-writer collector flow through CLI.
- Retry/backoff logic for ingestion with FloodWait handling.
- Channels control API (`GET /channels`, `PATCH /channels/{id}`).
- Feed API (`GET /feed`) and status API (`GET /status`).
- Streamlit UI with channel filter.
- Alembic migrations as primary DB init path.

## Quick start

1. Create env file:

```bash
copy .env.example .env
```

2. Install deps:

```bash
uv sync
```

3. Initialize DB (Alembic):

```bash
uv run python -m tgaggerator.cli init-db
```

4. Login:

```bash
uv run python -m tgaggerator.cli login
```

5. Sync channels and bootstrap messages:

```bash
uv run python -m tgaggerator.cli sync-channels
uv run python -m tgaggerator.cli bootstrap --limit 200
```

6. Start collector loop:

```bash
uv run python -m tgaggerator.cli ingest-loop --interval 30
```

7. Start API:

```bash
uv run python scripts/run_api.py
```

8. Start UI:

```bash
uv run streamlit run src/tgaggerator/ui/app.py
```

## API

- `GET /health`
- `GET /status`
- `GET /channels`
- `PATCH /channels/{channel_id}` body: `{ "enabled": bool?, "muted": bool? }`
- `GET /feed?q=&channel_ids=&only_media=&limit=&offset=`

## Notes

- Keep `.env` and session files private.
- Collector should remain a single writer process.
- Tests use lightweight schema init (`init_db_for_tests`).
