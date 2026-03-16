# 08 API Reference

Base URL: `http://127.0.0.1:8000`

## GET /health

Returns service health.

Response:

```json
{ "ok": true }
```

## GET /status

Returns aggregate ingestion status.

Response fields:
- `total_channels`
- `enabled_channels`
- `total_messages`
- `states[]` with per-channel sync metadata

## GET /channels

Returns all channels known to the system.

Fields:
- `id`, `tg_id`, `title`, `username`
- `is_private`, `enabled`, `muted`
- `last_msg_id`, `last_ok_at`, `last_error`

## PATCH /channels/{channel_id}

Updates one channel flags.

Request body:

```json
{
  "enabled": true,
  "muted": false
}
```

Rules:
- At least one of `enabled` or `muted` must be provided.

## PATCH /channels

Batch updates multiple channels.

Request body:

```json
{
  "channel_ids": [1, 2, 3],
  "enabled": true,
  "muted": false
}
```

Rules:
- `channel_ids` must not be empty.
- At least one of `enabled` or `muted` must be provided.

## GET /feed

Returns chronological feed entries.

Query params:
- `q` (string, optional)
- `channel_ids` (repeatable int param)
- `only_media` (bool)
- `limit` (1..500)
- `offset` (>=0)

Example:

```bash
curl "http://127.0.0.1:8000/feed?only_media=false&limit=50"
```
