from __future__ import annotations

import logging
from typing import Callable

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from tgaggerator.config import settings
from tgaggerator.db import SessionLocal
from tgaggerator.ingest.gateway import TelegramGateway
from tgaggerator.repository import upsert_channel

LOGGER = logging.getLogger("tgaggerator.telegram_ui")


def _is_allowed(update: Update) -> bool:
    if settings.tg_bot_allowed_chat_id is None:
        return True
    chat_id = update.effective_chat.id if update.effective_chat else None
    return chat_id == settings.tg_bot_allowed_chat_id


async def _guarded(update: Update, handler: Callable[[Update, ContextTypes.DEFAULT_TYPE], object], context):
    if not _is_allowed(update):
        await update.message.reply_text("Access denied for this chat")
        return
    await handler(update, context)


def _api_get(path: str, params: dict | None = None):
    base = settings.ui_api_base.rstrip("/")
    resp = requests.get(f"{base}{path}", params=params, timeout=15)
    resp.raise_for_status()
    return resp


def _api_patch(path: str, payload: dict):
    base = settings.ui_api_base.rstrip("/")
    resp = requests.patch(f"{base}{path}", json=payload, timeout=15)
    resp.raise_for_status()
    return resp


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "TGaggregator bot commands:\n"
        "/latest [N] - latest feed items\n"
        "/channels - list channels\n"
        "/enable <id> /disable <id>\n"
        "/mute <id> /unmute <id>\n"
        "/add <@channel or t.me/...> - add channel to catalog"
    )
    await update.message.reply_text(text)


async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    limit = 10
    if context.args:
        try:
            limit = max(1, min(20, int(context.args[0])))
        except Exception:
            limit = 10

    resp = _api_get("/feed", params={"limit": limit, "offset": 0})
    items = resp.json()
    if not items:
        await update.message.reply_text("Feed is empty")
        return

    lines: list[str] = []
    for item in items:
        header = f"[{item['channel_title']}] #{item['tg_message_id']}"
        text = (item.get("text") or "").strip().replace("\n", " ")
        snippet = text[:220] + ("..." if len(text) > 220 else "")
        link = item.get("link") or ""
        lines.append(f"{header}\n{snippet}\n{link}".strip())

    chunks: list[str] = []
    current = ""
    for line in lines:
        if len(current) + len(line) + 2 > 3500:
            chunks.append(current)
            current = line
        else:
            current = (current + "\n\n" + line).strip()
    if current:
        chunks.append(current)

    for chunk in chunks:
        await update.message.reply_text(chunk)


async def channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    resp = _api_get("/channels")
    items = resp.json()
    if not items:
        await update.message.reply_text("No channels in catalog")
        return

    lines = ["Channels:"]
    for item in items[:50]:
        flags = []
        flags.append("EN" if item.get("enabled") else "DIS")
        flags.append("MUTED" if item.get("muted") else "LIVE")
        lines.append(f"{item['id']}: {item['title']} ({', '.join(flags)})")

    await update.message.reply_text("\n".join(lines))


def _parse_id(args: list[str]) -> int:
    if not args:
        raise ValueError("Missing channel id")
    return int(args[0])


async def _toggle(update: Update, args: list[str], payload: dict, label: str) -> None:
    channel_id = _parse_id(args)
    resp = _api_patch(f"/channels/{channel_id}", payload)
    item = resp.json()
    await update.message.reply_text(f"{label}: {item['id']} {item['title']}")


async def enable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _toggle(update, context.args, {"enabled": True}, "Enabled")


async def disable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _toggle(update, context.args, {"enabled": False}, "Disabled")


async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _toggle(update, context.args, {"muted": True}, "Muted")


async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _toggle(update, context.args, {"muted": False}, "Unmuted")


async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /add @channel or /add https://t.me/channel")
        return

    handle = context.args[0]
    gateway = TelegramGateway()
    try:
        channel = await gateway.resolve_channel(handle)
    finally:
        await gateway.disconnect()

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

    await update.message.reply_text(f"Added: {channel.title} ({channel.tg_id})")


async def _guard_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _guarded(update, start, context)


async def _guard_latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _guarded(update, latest, context)


async def _guard_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _guarded(update, channels, context)


async def _guard_enable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _guarded(update, enable, context)


async def _guard_disable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _guarded(update, disable, context)


async def _guard_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _guarded(update, mute, context)


async def _guard_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _guarded(update, unmute, context)


async def _guard_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _guarded(update, add_channel, context)


def build_app() -> Application:
    if not settings.tg_bot_token:
        raise RuntimeError("TG_BOT_TOKEN is required for Telegram UI")

    app = Application.builder().token(settings.tg_bot_token).build()
    app.add_handler(CommandHandler("start", _guard_start))
    app.add_handler(CommandHandler("latest", _guard_latest))
    app.add_handler(CommandHandler("channels", _guard_channels))
    app.add_handler(CommandHandler("enable", _guard_enable))
    app.add_handler(CommandHandler("disable", _guard_disable))
    app.add_handler(CommandHandler("mute", _guard_mute))
    app.add_handler(CommandHandler("unmute", _guard_unmute))
    app.add_handler(CommandHandler("add", _guard_add))
    return app


def run_bot() -> None:
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    bot = build_app()
    LOGGER.info("Starting Telegram UI bot")
    bot.run_polling()
