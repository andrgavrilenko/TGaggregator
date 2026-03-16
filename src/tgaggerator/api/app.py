from datetime import UTC, datetime
from threading import Lock

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from tgaggerator.db import SessionLocal, get_db
from tgaggerator.config import settings
from tgaggerator.ingest.dto import MessageDTO
from tgaggerator.ingest.gateway import TelegramGateway
from tgaggerator.ingest.public_web import fetch_channel_info, fetch_recent_messages, normalize_username
from tgaggerator.init_db import init_db
from tgaggerator.repository import (
    get_enabled_channels,
    get_feed,
    get_metrics,
    get_or_create_state,
    get_status,
    insert_message_if_new,
    list_channels,
    mark_error,
    mark_success,
    set_channel_flags,
    set_channels_flags,
    upsert_channel,
)

app = FastAPI(title="tgaggerator API", version="0.1.0")
OPS_LOCK = Lock()
LOGIN_CHALLENGE: dict[str, str] = {}


class FeedItem(BaseModel):
    channel_id: int
    channel_title: str
    tg_message_id: int
    date_utc: str
    text: str | None
    media_type: str | None
    link: str | None


class ChannelItem(BaseModel):
    id: int
    tg_id: int
    title: str
    username: str | None
    is_private: bool
    enabled: bool
    muted: bool
    last_msg_id: int
    last_ok_at: str | None
    last_error: str | None


class ChannelPatch(BaseModel):
    enabled: bool | None = None
    muted: bool | None = None


class ChannelBatchPatch(BaseModel):
    channel_ids: list[int] = Field(min_length=1)
    enabled: bool | None = None
    muted: bool | None = None


class LoginRequest(BaseModel):
    phone: str | None = None


class LoginConfirmRequest(BaseModel):
    code: str
    password: str | None = None
    phone: str | None = None


class BootstrapRequest(BaseModel):
    limit: int = Field(default=200, ge=1, le=2000)


class StartRequest(BaseModel):
    bootstrap_limit: int = Field(default=200, ge=20, le=2000)
    run_ingest_once: bool = True


class PublicAddRequest(BaseModel):
    handle: str


async def _sync_channels_impl() -> int:
    gateway = TelegramGateway()
    try:
        channels = await gateway.list_channels()
    finally:
        await gateway.disconnect()

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
    return len(channels)


def _configured_public_handles() -> list[str]:
    raw = settings.public_channels or ""
    if not raw.strip():
        return []
    handles = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            handles.append(normalize_username(part))
        except ValueError:
            continue
    return sorted(set(handles))


def _upsert_public_channel(handle: str) -> dict:
    info = fetch_channel_info(handle)
    with SessionLocal() as db:
        ch = upsert_channel(
            db,
            tg_id=info.tg_id,
            title=info.title,
            username=info.username,
            is_private=False,
            enabled=True,
        )
        db.commit()
        state = get_or_create_state(db, ch.id)
        db.commit()
        return {
            "id": ch.id,
            "tg_id": ch.tg_id,
            "title": ch.title,
            "username": ch.username,
            "last_msg_id": state.last_msg_id,
        }


def _sync_public_channels_impl() -> int:
    handles = _configured_public_handles()
    synced = 0
    for handle in handles:
        try:
            _upsert_public_channel(handle)
            synced += 1
        except Exception:
            continue
    return synced


def _ingest_public_impl(limit_per_channel: int | None) -> dict:
    inserted_total = 0
    processed = 0
    failed = 0

    with SessionLocal() as db:
        channels = get_enabled_channels(db)

    for channel in channels:
        if channel.is_private or not channel.username:
            continue

        with SessionLocal() as db:
            state = get_or_create_state(db, channel.id)
            min_id = state.last_msg_id or 0
            local_inserted = 0
            max_msg_id = state.last_msg_id or 0
            last_seen_date = None

            try:
                messages = fetch_recent_messages(channel.username, limit=limit_per_channel or 200)
                for msg in messages:
                    if msg.tg_message_id <= min_id:
                        continue
                    is_new = insert_message_if_new(
                        db,
                        channel_id=channel.id,
                        tg_message_id=msg.tg_message_id,
                        date_utc=msg.date_utc,
                        text=msg.text,
                        media_type=msg.media_type,
                        views=None,
                        forwards=None,
                        link=msg.link,
                        raw_json=msg.raw_json,
                    )
                    if is_new:
                        local_inserted += 1
                    max_msg_id = max(max_msg_id, msg.tg_message_id)
                    last_seen_date = msg.date_utc

                lag_sec = None
                if last_seen_date:
                    lag_sec = int((datetime.now(UTC) - last_seen_date).total_seconds())
                mark_success(db, channel_id=channel.id, last_msg_id=max_msg_id, lag_sec=lag_sec)
                db.commit()
                inserted_total += local_inserted
                processed += 1
            except Exception as exc:
                db.rollback()
                mark_error(db, channel_id=channel.id, message=f"public-ingest: {exc}")
                db.commit()
                failed += 1

    return {
        "channels_total": processed + failed,
        "channels_processed": processed,
        "channels_failed": failed,
        "inserted": inserted_total,
    }


async def _ingest_impl(limit_per_channel: int | None) -> dict:
    gateway = TelegramGateway()
    inserted_total = 0
    processed = 0
    failed = 0

    await gateway.connect()
    try:
        entities = await gateway.map_dialog_entities()
        with SessionLocal() as db:
            channels = get_enabled_channels(db)

        for channel in channels:
            entity = entities.get(channel.tg_id)
            if entity is None:
                with SessionLocal() as db:
                    mark_error(db, channel_id=channel.id, message="Entity not found in dialogs")
                    db.commit()
                failed += 1
                continue

            with SessionLocal() as db:
                state = get_or_create_state(db, channel.id)
                min_id = state.last_msg_id or 0
                local_inserted = 0
                max_msg_id = state.last_msg_id or 0
                last_seen_date = None

                try:
                    async for msg in gateway.iter_messages(
                        entity=entity,
                        min_id=min_id,
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
                    inserted_total += local_inserted
                    processed += 1
                except Exception as exc:
                    db.rollback()
                    mark_error(db, channel_id=channel.id, message=str(exc))
                    db.commit()
                    failed += 1
    finally:
        await gateway.disconnect()

    return {
        "channels_total": processed + failed,
        "channels_processed": processed,
        "channels_failed": failed,
        "inserted": inserted_total,
    }


def _ops_lock_or_409() -> None:
    if not OPS_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Another operation is in progress")


def _ops_unlock() -> None:
    if OPS_LOCK.locked():
        OPS_LOCK.release()


async def _tg_authorized_state() -> tuple[bool, str | None]:
    if not settings.tg_api_id or not settings.tg_api_hash:
        return False, "TG_API_ID/TG_API_HASH are not configured"
    gateway = TelegramGateway()
    try:
        authorized = await gateway.is_authorized()
        return authorized, None
    except Exception as exc:
        return False, str(exc)
    finally:
        await gateway.disconnect()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/ops/status")
async def ops_status() -> dict:
    public_handles = _configured_public_handles()
    env = {
        "tg_api_configured": bool(settings.tg_api_id and settings.tg_api_hash),
        "tg_phone_configured": bool(settings.tg_phone),
        "tg_bot_configured": bool(settings.tg_bot_token),
        "public_channels_configured": len(public_handles),
    }

    authorized, auth_error = await _tg_authorized_state()

    has_challenge = bool(LOGIN_CHALLENGE.get("phone") and LOGIN_CHALLENGE.get("phone_code_hash"))
    return {
        "env": env,
        "tg_authorized": authorized,
        "login_challenge_pending": has_challenge,
        "auth_error": auth_error,
        "public_handles": public_handles,
    }


@app.post("/ops/init-db")
def ops_init_db() -> dict:
    _ops_lock_or_409()
    try:
        init_db()
        return {"ok": True, "message": "Database initialized"}
    finally:
        _ops_unlock()


@app.post("/ops/login/request-code")
async def ops_login_request_code(payload: LoginRequest) -> dict:
    phone = (payload.phone or settings.tg_phone or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Phone is required")

    _ops_lock_or_409()
    try:
        gateway = TelegramGateway()
        try:
            phone_code_hash = await gateway.request_login_code(phone)
        finally:
            await gateway.disconnect()
        LOGIN_CHALLENGE["phone"] = phone
        LOGIN_CHALLENGE["phone_code_hash"] = phone_code_hash
        return {"ok": True, "message": "Code sent"}
    finally:
        _ops_unlock()


@app.post("/ops/login/confirm")
async def ops_login_confirm(payload: LoginConfirmRequest) -> dict:
    phone = (payload.phone or LOGIN_CHALLENGE.get("phone") or settings.tg_phone or "").strip()
    phone_code_hash = LOGIN_CHALLENGE.get("phone_code_hash")
    if not phone:
        raise HTTPException(status_code=400, detail="Phone is required")

    _ops_lock_or_409()
    try:
        gateway = TelegramGateway()
        try:
            await gateway.sign_in_with_code(
                phone=phone,
                code=payload.code.strip(),
                phone_code_hash=phone_code_hash,
                password=(payload.password or None),
            )
        except RuntimeError as exc:
            if str(exc) == "2FA_REQUIRED":
                raise HTTPException(status_code=400, detail="2FA password required")
            raise
        finally:
            await gateway.disconnect()
        LOGIN_CHALLENGE.clear()
        return {"ok": True, "message": "Login successful"}
    finally:
        _ops_unlock()


@app.post("/ops/public/add")
def ops_public_add(payload: PublicAddRequest) -> dict:
    _ops_lock_or_409()
    try:
        try:
            item = _upsert_public_channel(payload.handle)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"ok": True, "channel": item}
    finally:
        _ops_unlock()


@app.post("/ops/sync-channels")
async def ops_sync_channels() -> dict:
    _ops_lock_or_409()
    try:
        authorized, _ = await _tg_authorized_state()
        if authorized:
            count = await _sync_channels_impl()
            return {"ok": True, "mode": "telegram", "channels_synced": count}

        count = _sync_public_channels_impl()
        return {"ok": True, "mode": "public", "channels_synced": count}
    finally:
        _ops_unlock()


@app.post("/ops/bootstrap")
async def ops_bootstrap(payload: BootstrapRequest) -> dict:
    _ops_lock_or_409()
    try:
        authorized, _ = await _tg_authorized_state()
        if authorized:
            result = await _ingest_impl(limit_per_channel=payload.limit)
            return {"ok": True, "mode": "telegram", **result}

        result = _ingest_public_impl(limit_per_channel=payload.limit)
        return {"ok": True, "mode": "public", **result}
    finally:
        _ops_unlock()


@app.post("/ops/ingest-once")
async def ops_ingest_once() -> dict:
    _ops_lock_or_409()
    try:
        authorized, _ = await _tg_authorized_state()
        if authorized:
            result = await _ingest_impl(limit_per_channel=None)
            return {"ok": True, "mode": "telegram", **result}

        result = _ingest_public_impl(limit_per_channel=None)
        return {"ok": True, "mode": "public", **result}
    finally:
        _ops_unlock()


@app.post("/ops/start")
async def ops_start(payload: StartRequest) -> dict:
    """One-shot startup pipeline for no-terminal usage.

    Steps:
      1) init DB
      2) check Telegram authorization
      3) sync channels
      4) bootstrap history
      5) optional ingest-once
    """
    _ops_lock_or_409()
    try:
        init_db()

        authorized, auth_error = await _tg_authorized_state()
        if not authorized:
            synced = _sync_public_channels_impl()
            boot = _ingest_public_impl(limit_per_channel=payload.bootstrap_limit)
            ingest = _ingest_public_impl(limit_per_channel=None) if payload.run_ingest_once else None

            if synced == 0 and boot.get("channels_total", 0) == 0:
                return {
                    "ok": False,
                    "requires_login": True,
                    "mode": "public",
                    "message": "Add at least one public channel (@username) or configure PUBLIC_CHANNELS in .env",
                    "auth_error": auth_error,
                }

            return {
                "ok": True,
                "requires_login": False,
                "mode": "public",
                "channels_synced": synced,
                "bootstrap": boot,
                "ingest_once": ingest,
            }

        synced = await _sync_channels_impl()
        boot = await _ingest_impl(limit_per_channel=payload.bootstrap_limit)
        ingest = await _ingest_impl(limit_per_channel=None) if payload.run_ingest_once else None
        return {
            "ok": True,
            "requires_login": False,
            "mode": "telegram",
            "channels_synced": synced,
            "bootstrap": boot,
            "ingest_once": ingest,
        }
    finally:
        _ops_unlock()


@app.get("/status")
def status(db: Session = Depends(get_db)) -> dict:
    return get_status(db)


@app.get("/metrics")
def metrics(db: Session = Depends(get_db)) -> Response:
    m = get_metrics(db)
    lines = [
        "# HELP tgaggerator_channels_total Total channels in catalog",
        "# TYPE tgaggerator_channels_total gauge",
        f"tgaggerator_channels_total {m['channels_total']}",
        "# HELP tgaggerator_channels_enabled Enabled channels",
        "# TYPE tgaggerator_channels_enabled gauge",
        f"tgaggerator_channels_enabled {m['channels_enabled']}",
        "# HELP tgaggerator_channels_muted Muted channels",
        "# TYPE tgaggerator_channels_muted gauge",
        f"tgaggerator_channels_muted {m['channels_muted']}",
        "# HELP tgaggerator_messages_total Total ingested messages",
        "# TYPE tgaggerator_messages_total gauge",
        f"tgaggerator_messages_total {m['messages_total']}",
        "# HELP tgaggerator_channels_with_error Channels with non-empty last_error",
        "# TYPE tgaggerator_channels_with_error gauge",
        f"tgaggerator_channels_with_error {m['channels_with_error']}",
        "# HELP tgaggerator_ingest_error_events_total Total recorded ingestion errors",
        "# TYPE tgaggerator_ingest_error_events_total counter",
        f"tgaggerator_ingest_error_events_total {m['ingest_error_events_total']}",
        "# HELP tgaggerator_metrics_generated_unixtime Metrics generation timestamp",
        "# TYPE tgaggerator_metrics_generated_unixtime gauge",
        f"tgaggerator_metrics_generated_unixtime {int(datetime.now(UTC).timestamp())}",
    ]
    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/channels", response_model=list[ChannelItem])
def channels(db: Session = Depends(get_db)) -> list[ChannelItem]:
    return [ChannelItem(**item) for item in list_channels(db)]


@app.patch("/channels/{channel_id}", response_model=ChannelItem)
def patch_channel(channel_id: int, payload: ChannelPatch, db: Session = Depends(get_db)) -> ChannelItem:
    if payload.enabled is None and payload.muted is None:
        raise HTTPException(status_code=400, detail="At least one field must be set")

    updated = set_channel_flags(
        db,
        channel_id=channel_id,
        enabled=payload.enabled,
        muted=payload.muted,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Channel not found")

    db.commit()
    items = list_channels(db)
    selected = next((item for item in items if item["id"] == channel_id), None)
    if selected is None:
        raise HTTPException(status_code=404, detail="Channel not found after update")
    return ChannelItem(**selected)


@app.patch("/channels", response_model=list[ChannelItem])
def patch_channels(payload: ChannelBatchPatch, db: Session = Depends(get_db)) -> list[ChannelItem]:
    if payload.enabled is None and payload.muted is None:
        raise HTTPException(status_code=400, detail="At least one field must be set")

    updated_ids = set_channels_flags(
        db,
        channel_ids=payload.channel_ids,
        enabled=payload.enabled,
        muted=payload.muted,
    )
    if not updated_ids:
        raise HTTPException(status_code=404, detail="No channels were updated")

    db.commit()
    items = list_channels(db)
    selected = [ChannelItem(**item) for item in items if item["id"] in set(updated_ids)]
    return selected


@app.get("/feed", response_model=list[FeedItem])
def feed(
    q: str | None = Query(default=None),
    channel_ids: list[int] = Query(default=[]),
    only_media: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    rows = get_feed(
        db,
        q=q,
        channel_ids=channel_ids or None,
        only_media=only_media,
        limit=limit,
        offset=offset,
    )
    return [
        FeedItem(
            channel_id=channel.id,
            channel_title=channel.title,
            tg_message_id=msg.tg_message_id,
            date_utc=msg.date_utc.isoformat(),
            text=msg.text,
            media_type=msg.media_type,
            link=msg.link,
        )
        for msg, channel in rows
    ]

