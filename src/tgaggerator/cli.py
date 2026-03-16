import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import os
import signal
import socket
import subprocess
import sys
import time

import typer
from telethon.errors import FloodWaitError

from tgaggerator.config import settings
from tgaggerator.db import SessionLocal
from tgaggerator.ingest.collector_lock import CollectorAlreadyRunningError, collector_lock
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
PROJECT_ROOT = Path(__file__).resolve().parents[2]
STACK_PID_FILE = PROJECT_ROOT / "data" / "runtime" / "stack_pids.json"


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


def _api_env(api_port: int) -> dict[str, str]:
    env = os.environ.copy()
    env["API_HOST"] = "127.0.0.1"
    env["API_PORT"] = str(api_port)
    return env


def _ui_env(api_port: int) -> dict[str, str]:
    env = os.environ.copy()
    env["UI_API_BASE"] = f"http://127.0.0.1:{api_port}"
    return env


def _build_stack_specs(
    *,
    interval: int,
    api_port: int,
    ui_port: int,
    collector: bool,
    api: bool,
    ui: bool,
    with_bot: bool,
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    if collector:
        specs.append(
            {
                "name": "collector",
                "cmd": [
                    sys.executable,
                    "-m",
                    "tgaggerator.cli",
                    "ingest-loop",
                    "--interval",
                    str(interval),
                ],
                "env": os.environ.copy(),
            }
        )
    if api:
        specs.append(
            {
                "name": "api",
                "cmd": [sys.executable, "scripts/run_api.py"],
                "env": _api_env(api_port),
            }
        )
    if ui:
        specs.append(
            {
                "name": "ui",
                "cmd": [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "src/tgaggerator/ui/app.py",
                    "--server.address",
                    "127.0.0.1",
                    "--server.port",
                    str(ui_port),
                ],
                "env": _ui_env(api_port),
            }
        )
    if with_bot:
        specs.append(
            {
                "name": "telegram-ui",
                "cmd": [sys.executable, "scripts/run_telegram_ui.py"],
                "env": _ui_env(api_port),
            }
        )
    return specs


def _is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        res = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            check=False,
            capture_output=True,
            text=True,
        )
        out = (res.stdout or "").strip()
        if not out or out.lower().startswith("info:"):
            return False
        for line in out.splitlines():
            row = line.strip()
            if not row or row.lower().startswith("info:"):
                continue
            cols = [part.strip().strip('"') for part in row.split('","')]
            if len(cols) >= 2 and cols[1].isdigit() and int(cols[1]) == pid:
                return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _kill_pid(pid: int) -> None:
    if pid <= 0:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            capture_output=True,
            text=True,
        )
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


def _read_stack_state() -> dict[str, Any] | None:
    if not STACK_PID_FILE.exists():
        return None
    try:
        return json.loads(STACK_PID_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_stack_state(specs: list[dict[str, Any]]) -> None:
    STACK_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "started_at": datetime.now(UTC).isoformat(),
        "cwd": str(PROJECT_ROOT),
        "processes": [
            {
                "name": spec["name"],
                "pid": spec["pid"],
                "cmd": spec["cmd"],
            }
            for spec in specs
        ],
    }
    STACK_PID_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _clear_stack_state() -> None:
    if STACK_PID_FILE.exists():
        STACK_PID_FILE.unlink()


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


@app.command("add-channel")
def add_channel_cmd(handle: str = typer.Argument(..., help="@channel or https://t.me/channel")) -> None:
    gateway = TelegramGateway()
    channel = run(gateway.resolve_channel(handle))
    run(gateway.disconnect())

    with SessionLocal() as db:
        upsert_channel(
            db,
            tg_id=channel.tg_id,
            title=channel.title,
            username=channel.username,
            is_private=channel.is_private,
            enabled=True,
        )
        db.commit()

    typer.echo(f"Added channel: {channel.title} ({channel.tg_id})")


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


async def _refresh_entities(gateway: TelegramGateway) -> dict[int, object]:
    return await gateway.map_dialog_entities()


async def _ingest_once_core(
    gateway: TelegramGateway,
    entities: dict[int, object],
    limit_per_channel: int | None,
) -> tuple[int, int, dict[int, object]]:
    inserted = 0
    processed_channels = 0

    with SessionLocal() as db:
        channels = get_enabled_channels(db)

    for channel in channels:
        entity = entities.get(channel.tg_id)
        if entity is None:
            try:
                entities = await _refresh_entities(gateway)
                entity = entities.get(channel.tg_id)
            except Exception as exc:
                with SessionLocal() as db:
                    mark_error(db, channel_id=channel.id, message=f"Entity refresh failed: {exc}")
                    db.commit()
                log_event(
                    "channel_entity_refresh_failed",
                    channel_id=channel.id,
                    channel_title=channel.title,
                    error=str(exc),
                )

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

    return inserted, processed_channels, entities


async def _ingest_once(limit_per_channel: int | None) -> tuple[int, int]:
    gateway = TelegramGateway()
    await gateway.connect()

    try:
        entities = await _refresh_entities(gateway)
        inserted, processed_channels, _ = await _ingest_once_core(gateway, entities, limit_per_channel)
        return inserted, processed_channels
    finally:
        await gateway.disconnect()


async def _ingest_loop(every: int) -> None:
    gateway = TelegramGateway()
    await gateway.connect()
    entities = await _refresh_entities(gateway)

    try:
        while True:
            tick_started = datetime.now(UTC)
            try:
                inserted, channels, entities = await _ingest_once_core(gateway, entities, None)
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

            await asyncio.sleep(every)
    finally:
        await gateway.disconnect()


def _with_collector_lock(fn):
    try:
        with collector_lock(settings.collector_lock_path):
            return fn()
    except CollectorAlreadyRunningError:
        typer.echo("Collector is already running (lock is held).")
        raise typer.Exit(code=2)


@app.command("bootstrap")
def bootstrap_cmd(limit: int = typer.Option(None, help="Messages per channel")) -> None:
    if limit is None:
        limit = settings.default_bootstrap_limit

    def _run_once():
        inserted, channels = run(_ingest_once(limit))
        typer.echo(f"Bootstrap complete. channels={channels}, inserted={inserted}")

    _with_collector_lock(_run_once)


@app.command("ingest-once")
def ingest_once_cmd(limit: int = typer.Option(None, help="Messages per channel, optional")) -> None:
    def _run_once():
        inserted, channels = run(_ingest_once(limit))
        typer.echo(f"Ingest complete. channels={channels}, inserted={inserted}")

    _with_collector_lock(_run_once)


@app.command("ingest-loop")
def ingest_loop_cmd(interval: int = typer.Option(None, help="Loop interval seconds")) -> None:
    every = interval or settings.ingest_interval_sec

    def _run_loop():
        run(_ingest_loop(every))

    _with_collector_lock(_run_loop)


@app.command("up")
def up_cmd(
    collector: bool = typer.Option(True, "--collector/--no-collector", help="Start collector"),
    api: bool = typer.Option(True, "--api/--no-api", help="Start API"),
    ui: bool = typer.Option(True, "--ui/--no-ui", help="Start Streamlit web UI"),
    with_bot: bool = typer.Option(False, "--with-bot", help="Start Telegram bot UI too"),
    interval: int = typer.Option(None, help="Collector interval in seconds"),
    api_port: int = typer.Option(None, help="API port override"),
    ui_port: int = typer.Option(8502, help="Web UI port"),
    detach: bool = typer.Option(True, "--detach/--foreground", help="Run in background"),
) -> None:
    """Start collector + API + web UI as one local service stack."""
    if not any([collector, api, ui, with_bot]):
        typer.echo("Nothing to start. Enable at least one component.")
        raise typer.Exit(code=2)

    if collector and (not settings.tg_api_id or not settings.tg_api_hash):
        typer.echo("Collector requires TG_API_ID and TG_API_HASH in .env.")
        raise typer.Exit(code=2)

    if with_bot and not settings.tg_bot_token:
        typer.echo("Bot UI requires TG_BOT_TOKEN in .env.")
        raise typer.Exit(code=2)

    state = _read_stack_state()
    if state:
        alive = [p for p in state.get("processes", []) if _pid_alive(int(p.get("pid", 0)))]
        if alive:
            typer.echo("Stack already running. Use `python -m tgaggerator.cli down` first.")
            raise typer.Exit(code=2)

    every = interval or settings.ingest_interval_sec
    api_port_value = api_port or settings.api_port
    if api and not _is_port_free(api_port_value):
        typer.echo(f"API port is busy: {api_port_value}")
        raise typer.Exit(code=2)
    if ui and not _is_port_free(ui_port):
        typer.echo(f"UI port is busy: {ui_port}")
        raise typer.Exit(code=2)

    specs = _build_stack_specs(
        interval=every,
        api_port=api_port_value,
        ui_port=ui_port,
        collector=collector,
        api=api,
        ui=ui,
        with_bot=with_bot,
    )

    started_specs: list[dict[str, Any]] = []
    for spec in specs:
        proc = subprocess.Popen(
            spec["cmd"],
            cwd=str(PROJECT_ROOT),
            env=spec["env"],
        )
        spec["pid"] = proc.pid
        spec["process"] = proc
        started_specs.append(spec)
        typer.echo(f"Started {spec['name']}: pid={proc.pid}")

    # Give processes a moment to fail-fast (bad env, ports busy, etc.)
    time.sleep(2)
    failed = [spec for spec in started_specs if spec["process"].poll() is not None]
    if failed:
        for spec in failed:
            typer.echo(f"Failed to start {spec['name']}, exit={spec['process'].returncode}")
        for spec in started_specs:
            if spec not in failed and spec["process"].poll() is None:
                _kill_pid(spec["pid"])
        _clear_stack_state()
        raise typer.Exit(code=1)

    _write_stack_state(started_specs)
    summary = []
    if api:
        summary.append(f"API=http://127.0.0.1:{api_port_value}")
    if ui:
        summary.append(f"UI=http://127.0.0.1:{ui_port}")
    summary.append("BOT=on" if with_bot else "BOT=off")
    typer.echo("Stack up. " + "  ".join(summary))

    if detach:
        return

    try:
        while True:
            dead = [spec for spec in started_specs if spec["process"].poll() is not None]
            if dead:
                for spec in dead:
                    typer.echo(f"{spec['name']} exited, code={spec['process'].returncode}")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        typer.echo("Stopping stack...")
    finally:
        for spec in reversed(started_specs):
            _kill_pid(spec["pid"])
        _clear_stack_state()


@app.command("down")
def down_cmd() -> None:
    """Stop stack processes started by `up`."""
    state = _read_stack_state()
    if not state:
        typer.echo("Stack is not running (no PID state).")
        return

    processes = state.get("processes", [])
    stopped = 0
    for item in reversed(processes):
        pid = int(item.get("pid", 0))
        name = item.get("name", "unknown")
        if _pid_alive(pid):
            _kill_pid(pid)
            stopped += 1
            typer.echo(f"Stopped {name}: pid={pid}")
        else:
            typer.echo(f"Already stopped {name}: pid={pid}")

    _clear_stack_state()
    typer.echo(f"Stack down. Processes handled: {len(processes)}, stopped: {stopped}")


if __name__ == "__main__":
    app()
