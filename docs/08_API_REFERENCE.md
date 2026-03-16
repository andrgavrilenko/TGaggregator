# 08 API Reference

Base URL: `http://127.0.0.1:8000`

## Security model (current)

- API is expected to run on localhost/VPN.
- Built-in API auth is not enabled yet.

## GET /health

Returns service health.

```json
{ "ok": true }
```

## Ops endpoints (no-terminal onboarding)

### GET /ops/status

Returns onboarding/runtime status:
- env flags (`tg_api_configured`, `public_channels_configured`, etc.)
- `tg_authorized`
- `public_handles`

### POST /ops/start

One-click startup pipeline.

Request:
```json
{ "bootstrap_limit": 200, "run_ingest_once": true }
```

Behavior:
- If Telegram account is authorized: uses full Telegram mode.
- If not authorized: uses public-only mode (configured + manually added public channels).

### POST /ops/public/add

Adds one public Telegram channel by handle.

Request:
```json
{ "handle": "@telegram" }
```

### POST /ops/init-db
### POST /ops/login/request-code
### POST /ops/login/confirm
### POST /ops/sync-channels
### POST /ops/bootstrap
### POST /ops/ingest-once

## GET /status

Aggregate ingestion status.

Fields:
- `total_channels`
- `enabled_channels`
- `total_messages`
- `states[]` (per-channel sync metadata)

## GET /metrics

Prometheus-style metrics endpoint (`text/plain; version=0.0.4`).

Includes:
- `tgaggerator_channels_total`
- `tgaggerator_channels_enabled`
- `tgaggerator_channels_muted`
- `tgaggerator_messages_total`
- `tgaggerator_channels_with_error`
- `tgaggerator_ingest_error_events_total`

## GET /channels

Returns channel catalog.

Fields:
- `id`, `tg_id`, `title`, `username`
- `is_private`, `enabled`, `muted`
- `last_msg_id`, `last_ok_at`, `last_error`

## PATCH /channels/{channel_id}

Updates one channel.

```json
{ "enabled": true, "muted": false }
```

Rules:
- At least one of `enabled` or `muted` is required.

## PATCH /channels

Batch update for multiple channels.

```json
{
  "channel_ids": [1,2,3],
  "enabled": true,
  "muted": false
}
```

Rules:
- `channel_ids` must be non-empty.
- At least one of `enabled` or `muted` is required.

## GET /feed

Chronological feed.

Query params:
- `q` (optional text filter)
- `channel_ids` (repeatable int param)
- `only_media` (bool)
- `limit` (1..500)
- `offset` (>=0)

Example:

```bash
curl "http://127.0.0.1:8000/feed?limit=50&only_media=false"
```

## Semantics note

- `muted=true` means the channel is excluded from ingestion in current policy.
