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

    @staticmethod
    def _build_link(channel_tg_id: int, channel_username: str | None, message_id: int | None) -> str | None:
        if message_id is None:
            return None
        if channel_username:
            return f"https://t.me/{channel_username}/{message_id}"

        normalized = str(abs(channel_tg_id))
        if normalized.startswith("100"):
            normalized = normalized[3:]
        if not normalized:
            return None
        return f"https://t.me/c/{normalized}/{message_id}"

    @classmethod
    def from_telethon(
        cls,
        channel_tg_id: int,
        channel_username: str | None,
        msg,
    ) -> "MessageDTO":
        date_utc = msg.date.astimezone(UTC) if msg.date else datetime.now(UTC)
        media_type = type(msg.media).__name__ if msg.media is not None else None
        text = (msg.message or msg.text or None)
        link = cls._build_link(channel_tg_id, channel_username, getattr(msg, "id", None))

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
