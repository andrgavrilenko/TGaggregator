from __future__ import annotations

import re
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime

import requests
from bs4 import BeautifulSoup

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


@dataclass
class PublicChannelInfo:
    username: str
    title: str
    tg_id: int


@dataclass
class PublicMessage:
    tg_message_id: int
    date_utc: datetime
    text: str | None
    media_type: str | None
    link: str | None
    raw_json: dict | None


def normalize_username(handle: str) -> str:
    s = handle.strip()
    if not s:
        raise ValueError("Empty handle")
    if s.startswith("https://t.me/"):
        s = s.removeprefix("https://t.me/")
    if s.startswith("http://t.me/"):
        s = s.removeprefix("http://t.me/")
    if s.startswith("s/"):
        s = s[2:]
    s = s.lstrip("@").split("/")[0].strip()
    if not re.fullmatch(r"[A-Za-z0-9_]{3,64}", s):
        raise ValueError("Invalid channel username")
    return s


def synthetic_tg_id(username: str) -> int:
    # Deterministic synthetic id for public-only mode.
    return 2_000_000_000 + (zlib.crc32(username.encode("utf-8")) & 0x7FFFFFFF)


def fetch_channel_info(handle: str) -> PublicChannelInfo:
    username = normalize_username(handle)
    url = f"https://t.me/s/{username}"
    resp = requests.get(url, timeout=20, headers={"User-Agent": _UA})
    if resp.status_code >= 400:
        raise RuntimeError(f"Channel page fetch failed: {resp.status_code}")

    soup = BeautifulSoup(resp.text, "html.parser")
    title = (
        soup.select_one("meta[property='og:title']") or soup.select_one("title")
    )
    if title and title.get("content"):
        value = str(title.get("content")).strip()
    elif title:
        value = title.get_text(" ", strip=True)
    else:
        value = username

    # Common page title pattern is "<channel title> — Telegram"
    value = value.replace(" — Telegram", "").strip() or username
    return PublicChannelInfo(username=username, title=value, tg_id=synthetic_tg_id(username))


def _detect_media_type(node) -> str | None:
    if node.select_one("a.tgme_widget_message_photo_wrap"):
        return "photo"
    if node.select_one("video"):
        return "video"
    if node.select_one("a.tgme_widget_message_document_wrap"):
        return "document"
    return None


def fetch_recent_messages(handle: str, limit: int = 200) -> list[PublicMessage]:
    username = normalize_username(handle)
    url = f"https://t.me/s/{username}"
    resp = requests.get(url, timeout=20, headers={"User-Agent": _UA})
    if resp.status_code >= 400:
        raise RuntimeError(f"Channel feed fetch failed: {resp.status_code}")

    soup = BeautifulSoup(resp.text, "html.parser")
    items: list[PublicMessage] = []

    for wrap in soup.select("div.tgme_widget_message_wrap"):
        node = wrap.select_one("div.tgme_widget_message")
        if node is None:
            continue
        post = node.get("data-post")
        if not post or "/" not in post:
            continue
        try:
            msg_id = int(post.split("/")[-1])
        except ValueError:
            continue

        time_node = node.select_one("time")
        iso = time_node.get("datetime") if time_node else None
        if iso:
            try:
                date_utc = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(UTC)
            except ValueError:
                date_utc = datetime.now(UTC)
        else:
            date_utc = datetime.now(UTC)

        text_node = node.select_one("div.tgme_widget_message_text")
        text = text_node.get_text("\n", strip=True) if text_node else None

        link_node = node.select_one("a.tgme_widget_message_date")
        link = link_node.get("href") if link_node else f"https://t.me/{username}/{msg_id}"

        items.append(
            PublicMessage(
                tg_message_id=msg_id,
                date_utc=date_utc,
                text=text,
                media_type=_detect_media_type(node),
                link=link,
                raw_json={"source": "public_web", "username": username},
            )
        )

    items.sort(key=lambda m: m.tg_message_id)
    if limit > 0:
        return items[-limit:]
    return items
