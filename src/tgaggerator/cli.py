import asyncio
import json
import logging
import time
from datetime import UTC, datetime

import typer
from telethon.errors import FloodWaitError

from tgaggerator.config import settings
from tgaggerator.db import SessionLocal
from tgaggerator.ingest.dto import MessageDTO
from tgaggerator.ingest.gateway import TelegramGateway, run
from tgaggerator.init_db import init_db
from tgaggerator.repository import (
    get_enabled_channels,
    get_or_create_state,
    insert_message_if_new,
    mark_error,
    mark_success,
    upsert_channel,
)

app = typer.Typer(help="tgaggerator CLI")

LOG_LEVEL = getattr(logging, settings.log_level.upper(), logging.INFO)
logging.basicConfig(level=LOG_LEVEL, format="%(message)s")
LOGGER = logging.getLogger("tgaggerator.collector")


def log_event(event: str, **payload) -> None:
    message = {
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
        **payload,
    }
    LOGGER.info(json.dumps(message, ensure_ascii=False, default=str))


def _bounded_backoff(attempt: int) -> int:
    raw = settings.ingest_retry_base_sec * (2 ** max(attempt - 1, 0))
    return min(raw, settings.ingest_retry_max_sec)


@app.command("init-db")
def init_db_cmd() -> None:
    init_db()
    typer.echo("DB initialized via migrations")


@app.command("login")
def login_cmd() -> None:
    gateway = TelegramGateway()
    run(gateway.ensure_login())
    run(gateway.disconnect())
    typer.echo("Login successful")


@app.command("sync-channels")
def sync_channels_cmd() -> None:
    gateway = TelegramGateway()
    channels = run(gateway.list_channels())
    run(gateway.disconnect())

    with SessionLocal() as db:
        for ch in channels:
            upsert_channel(
                db,
                tg_id=ch.tg_id,
                title=ch.title,
                username=ch.username,
                is_private=ch.is_private,
            )
        db.commit()

    typer.echo(f"Synced channels: {len(channels)}")


async def _ingest_channel_with_retry(
    gateway: TelegramGateway,
    *,
    entity: object,
    channel,
    limit_per_channel: int | None,
) -> int:
    with SessionLocal() as db:
        get_or_create_state(db, channel.id)

    for attempt in range(1, settings.ingest_max_retries + 1):
        with SessionLocal() as db:
            state = get_or_create_state(db, channel.id)
            local_inserted = 0
            max_msg_id = state.last_msg_id or 0
            last_seen_date: datetime | None = None

            try:
                async for msg in gateway.iter_messages(
                    entity=entity,
                    min_id=state.last_msg_id or 0,
                    limit=limit_per_channel,
                ):
                    dto = MessageDTO.from_telethon(channel.tg_id, channel.username, msg)
                    is_new = insert_message_if_new(
                        db,
                        channel_id=channel.id,
                        tg_message_id=dto.tg_message_id,
                        date_utc=dto.date_utc,
                        text=dto.text,
                        media_type=dto.media_type,
                        views=dto.views,
                        forwards=dto.forwards,
                        link=dto.link,
                        raw_json=dto.raw_json,
                    )
                    if is_new:
                        local_inserted += 1
                    max_msg_id = max(max_msg_id, dto.tg_message_id)
                    last_seen_date = dto.date_utc

                lag_sec = None
                if last_seen_date:
                    lag_sec = int((datetime.now(UTC) - last_seen_date).total_seconds())
                mark_success(db, channel_id=channel.id, last_msg_id=max_msg_id, lag_sec=lag_sec)
                db.commit()
                log_event(
                    "channel_ingest_ok",
                    channel_id=channel.id,
                    channel_title=channel.title,
                    inserted=local_inserted,
                    last_msg_id=max_msg_id,
                    lag_sec=lag_sec,
                )
                return local_inserted

            except FloodWaitError as exc:
                db.rollback()
                wait_sec = int(getattr(exc, "seconds", getattr(exc, "value", 0)) or 0)
                mark_error(
                    db,
                    channel_id=channel.id,
                    message=f"FloodWait attempt={attempt}: wait={wait_sec}s",
                )
                db.commit()
                log_event(
                    "channel_ingest_floodwait",
                    channel_id=channel.id,
                    channel_title=channel.title,
                    attempt=attempt,
                    wait_sec=wait_sec,
                )

                if attempt >= settings.ingest_max_retries:
                    raise
                await asyncio.sleep(wait_sec + 1)

            except Exception as exc:
                db.rollback()
                mark_error(
                    db,
                    channel_id=channel.id,
                    message=f"Attempt={attempt}: {exc}",
                )
                db.commit()
                backoff = _bounded_backoff(attempt)
                log_event(
                    "channel_ingest_retry",
                    channel_id=channel.id,
                    channel_title=channel.title,
                    attempt=attempt,
                    backoff_sec=backoff,
                    error=str(exc),
                )

                if attempt >= settings.ingest_max_retries:
                    raise
                await asyncio.sleep(backoff)

    return 0


async def _ingest_once(limit_per_channel: int | None) -> tuple[int, int]:
    gateway = TelegramGateway()
    await gateway.connect()

    try:
        entities = await gateway.map_dialog_entities()
        inserted = 0
        processed_channels = 0

        with SessionLocal() as db:
            channels = get_enabled_channels(db)

        for channel in channels:
            entity = entities.get(channel.tg_id)
            if entity is None:
                with SessionLocal() as db:
                    mark_error(db, channel_id=channel.id, message="Entity not found in dialogs")
                    db.commit()
                log_event("channel_entity_missing", channel_id=channel.id, channel_title=channel.title)
                continue

            try:
                local_inserted = await _ingest_channel_with_retry(
                    gateway,
                    entity=entity,
                    channel=channel,
                    limit_per_channel=limit_per_channel,
                )
                inserted += local_inserted
                processed_channels += 1
            except Exception as exc:
                with SessionLocal() as db:
                    mark_error(db, channel_id=channel.id, message=f"Final failure: {exc}")
                    db.commit()
                log_event(
                    "channel_ingest_failed",
                    channel_id=channel.id,
                    channel_title=channel.title,
                    error=str(exc),
                )

        return inserted, processed_channels
    finally:
        await gateway.disconnect()


@app.command("bootstrap")
def bootstrap_cmd(limit: int = typer.Option(None, help="Messages per channel")) -> None:
    if limit is None:
        limit = settings.default_bootstrap_limit
    inserted, channels = run(_ingest_once(limit))
    typer.echo(f"Bootstrap complete. channels={channels}, inserted={inserted}")


@app.command("ingest-once")
def ingest_once_cmd(limit: int = typer.Option(None, help="Messages per channel, optional")) -> None:
    inserted, channels = run(_ingest_once(limit))
    typer.echo(f"Ingest complete. channels={channels}, inserted={inserted}")


@app.command("ingest-loop")
def ingest_loop_cmd(interval: int = typer.Option(None, help="Loop interval seconds")) -> None:
    every = interval or settings.ingest_interval_sec
    while True:
        tick_started = datetime.now(UTC)
        try:
            inserted, channels = run(_ingest_once(None))
            duration_ms = int((datetime.now(UTC) - tick_started).total_seconds() * 1000)
            log_event(
                "ingest_tick_ok",
                channels=channels,
                inserted=inserted,
                duration_ms=duration_ms,
            )
            typer.echo(f"Ingest tick: channels={channels}, inserted={inserted}")
        except Exception as exc:
            duration_ms = int((datetime.now(UTC) - tick_started).total_seconds() * 1000)
            log_event(
                "ingest_tick_failed",
                duration_ms=duration_ms,
                error=str(exc),
            )
            typer.echo(f"Ingest tick failed: {exc}")
        time.sleep(every)


if __name__ == "__main__":
    app()
