from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from tgaggerator.db import get_db
from tgaggerator.repository import (
    get_feed,
    get_status,
    list_channels,
    set_channel_flags,
    set_channels_flags,
)

app = FastAPI(title="tgaggerator API", version="0.1.0")


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


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/status")
def status(db: Session = Depends(get_db)) -> dict:
    return get_status(db)


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
