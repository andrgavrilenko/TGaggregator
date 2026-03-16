from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(slots=True)
class ChannelDTO:
    tg_id: int
    title: str
    username: str | None
    is_private: bool


@dataclass(slots=True)
class MessageDTO:
    channel_tg_id: int
    tg_message_id: int
    date_utc: datetime
    text: str | None
    media_type: str | None
    views: int | None
    forwards: int | None
    link: str | None
    raw_json: dict | None

    @classmethod
    def from_telethon(cls, channel_tg_id: int, msg) -> "MessageDTO":
        date_utc = msg.date.astimezone(UTC) if msg.date else datetime.now(UTC)
        media_type = type(msg.media).__name__ if msg.media is not None else None
        text = (msg.message or msg.text or None)

        link = None
        try:
            link = msg.to_id and msg.id and f"https://t.me/c/{str(channel_tg_id).replace('-100', '')}/{msg.id}"
        except Exception:
            link = None

        raw_json = None
        try:
            raw_json = msg.to_dict()
        except Exception:
            raw_json = None

        return cls(
            channel_tg_id=channel_tg_id,
            tg_message_id=msg.id,
            date_utc=date_utc,
            text=text,
            media_type=media_type,
            views=getattr(msg, "views", None),
            forwards=getattr(msg, "forwards", None),
            link=link,
            raw_json=raw_json,
        )
