# Agent A2 Data Ingestion

## Mission
Реализовать надежный ingestion из Telegram через MTProto.

## Tasks
- Login/session flow.
- Sync каналов.
- Bootstrap history.
- Incremental sync.
- Retry/FloodWait handling.

## Inputs
- Контракты БД от A1.

## Outputs
- CLI `login`, `sync-channels`, `ingest-once`, `ingest-loop`.
- Обновление `ingestion_state`.

## DoD
- Нет дублей сообщений.
- Синк устойчив к временным сбоям.
