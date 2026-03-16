from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from tgaggerator.models import Channel, IngestionState, Message


def upsert_channel(
    db: Session,
    *,
    tg_id: int,
    title: str,
    username: str | None,
    is_private: bool,
    enabled: bool = True,
) -> Channel:
    channel = db.scalar(select(Channel).where(Channel.tg_id == tg_id))
    if channel is None:
        channel = Channel(
            tg_id=tg_id,
            title=title,
            username=username,
            is_private=is_private,
            enabled=enabled,
        )
        db.add(channel)
        db.flush()

    channel.title = title
    channel.username = username
    channel.is_private = is_private

    state = db.scalar(select(IngestionState).where(IngestionState.channel_id == channel.id))
    if state is None:
        db.add(IngestionState(channel_id=channel.id, last_msg_id=0))

    return channel


def list_channels(db: Session) -> list[dict]:
    rows = db.execute(
        select(Channel, IngestionState)
        .outerjoin(IngestionState, IngestionState.channel_id == Channel.id)
        .order_by(Channel.title.asc())
    ).all()

    return [
        {
            "id": channel.id,
            "tg_id": channel.tg_id,
            "title": channel.title,
            "username": channel.username,
            "is_private": channel.is_private,
            "enabled": channel.enabled,
            "muted": channel.muted,
            "last_msg_id": state.last_msg_id if state else 0,
            "last_ok_at": state.last_ok_at.isoformat() if state and state.last_ok_at else None,
            "last_error": state.last_error if state else None,
        }
        for channel, state in rows
    ]


def set_channel_flags(
    db: Session,
    *,
    channel_id: int,
    enabled: bool | None = None,
    muted: bool | None = None,
) -> Channel | None:
    channel = db.scalar(select(Channel).where(Channel.id == channel_id))
    if channel is None:
        return None

    if enabled is not None:
        channel.enabled = enabled
    if muted is not None:
        channel.muted = muted

    db.flush()
    return channel


def set_channels_flags(
    db: Session,
    *,
    channel_ids: list[int],
    enabled: bool | None = None,
    muted: bool | None = None,
) -> list[int]:
    if not channel_ids:
        return []

    rows = db.scalars(select(Channel).where(Channel.id.in_(channel_ids))).all()
    updated_ids: list[int] = []

    for channel in rows:
        if enabled is not None:
            channel.enabled = enabled
        if muted is not None:
            channel.muted = muted
        updated_ids.append(channel.id)

    db.flush()
    return updated_ids


def get_enabled_channels(db: Session) -> list[Channel]:
    rows = db.scalars(select(Channel).where(and_(Channel.enabled.is_(True), Channel.muted.is_(False))))
    return list(rows)


def get_or_create_state(db: Session, channel_id: int) -> IngestionState:
    state = db.scalar(select(IngestionState).where(IngestionState.channel_id == channel_id))
    if state is None:
        state = IngestionState(channel_id=channel_id, last_msg_id=0)
        db.add(state)
        db.flush()
    return state


def insert_message_if_new(
    db: Session,
    *,
    channel_id: int,
    tg_message_id: int,
    date_utc: datetime,
    text: str | None,
    media_type: str | None,
    views: int | None,
    forwards: int | None,
    link: str | None,
    raw_json: dict | None,
) -> bool:
    existing = db.scalar(
        select(Message.id).where(
            and_(Message.channel_id == channel_id, Message.tg_message_id == tg_message_id)
        )
    )
    if existing is not None:
        return False

    db.add(
        Message(
            channel_id=channel_id,
            tg_message_id=tg_message_id,
            date_utc=date_utc,
            text=text,
            media_type=media_type,
            views=views,
            forwards=forwards,
            link=link,
            raw_json=raw_json,
        )
    )
    return True


def mark_success(db: Session, *, channel_id: int, last_msg_id: int, lag_sec: int | None) -> None:
    state = get_or_create_state(db, channel_id)
    state.last_msg_id = max(state.last_msg_id or 0, last_msg_id)
    state.last_ok_at = datetime.now(UTC)
    state.last_error = None
    state.lag_sec = lag_sec


def mark_error(db: Session, *, channel_id: int, message: str) -> None:
    state = get_or_create_state(db, channel_id)
    state.error_count = (state.error_count or 0) + 1
    state.last_error = message[:2000]


def get_feed(
    db: Session,
    *,
    q: str | None = None,
    channel_ids: list[int] | None = None,
    only_media: bool = False,
    limit: int = 100,
    offset: int = 0,
):
    stmt = (
        select(Message, Channel)
        .join(Channel, Message.channel_id == Channel.id)
        .order_by(Message.date_utc.desc(), Message.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if q:
        stmt = stmt.where(Message.text.ilike(f"%{q}%"))
    if channel_ids:
        stmt = stmt.where(Message.channel_id.in_(channel_ids))
    if only_media:
        stmt = stmt.where(Message.media_type.is_not(None))

    return db.execute(stmt).all()


def get_status(db: Session) -> dict:
    total_channels = db.scalar(select(func.count(Channel.id))) or 0
    enabled_channels = db.scalar(select(func.count(Channel.id)).where(Channel.enabled.is_(True))) or 0
    total_messages = db.scalar(select(func.count(Message.id))) or 0

    states = db.execute(
        select(
            Channel.id,
            Channel.title,
            IngestionState.last_msg_id,
            IngestionState.last_ok_at,
            IngestionState.last_error,
        )
        .join(IngestionState, IngestionState.channel_id == Channel.id)
        .order_by(Channel.title.asc())
    ).all()

    return {
        "total_channels": total_channels,
        "enabled_channels": enabled_channels,
        "total_messages": total_messages,
        "states": [
            {
                "channel_id": row.id,
                "channel": row.title,
                "last_msg_id": row.last_msg_id,
                "last_ok_at": row.last_ok_at.isoformat() if row.last_ok_at else None,
                "last_error": row.last_error,
            }
            for row in states
        ],
    }


def get_metrics(db: Session) -> dict[str, int]:
    total_channels = db.scalar(select(func.count(Channel.id))) or 0
    enabled_channels = db.scalar(select(func.count(Channel.id)).where(Channel.enabled.is_(True))) or 0
    muted_channels = db.scalar(select(func.count(Channel.id)).where(Channel.muted.is_(True))) or 0
    total_messages = db.scalar(select(func.count(Message.id))) or 0

    states_with_error = (
        db.scalar(
            select(func.count(IngestionState.channel_id)).where(IngestionState.last_error.is_not(None))
        )
        or 0
    )
    error_events = db.scalar(select(func.coalesce(func.sum(IngestionState.error_count), 0))) or 0

    return {
        "channels_total": int(total_channels),
        "channels_enabled": int(enabled_channels),
        "channels_muted": int(muted_channels),
        "messages_total": int(total_messages),
        "channels_with_error": int(states_with_error),
        "ingest_error_events_total": int(error_events),
    }
