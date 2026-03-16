import asyncio

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import Channel as TLChannel
from telethon.utils import get_peer_id

from tgaggerator.config import settings
from tgaggerator.ingest.dto import ChannelDTO


class TelegramGateway:
    def __init__(self) -> None:
        if not settings.tg_api_id or not settings.tg_api_hash:
            raise RuntimeError("TG_API_ID and TG_API_HASH must be set in environment")
        self.client = TelegramClient(settings.tg_session_path, settings.tg_api_id, settings.tg_api_hash)

    async def connect(self) -> None:
        await self.client.connect()

    async def disconnect(self) -> None:
        await self.client.disconnect()

    async def ensure_login(self) -> None:
        await self.connect()
        if await self.client.is_user_authorized():
            return

        if not settings.tg_phone:
            raise RuntimeError("TG_PHONE must be set for first login")

        await self.client.send_code_request(settings.tg_phone)
        code = input("Telegram code: ").strip()
        try:
            await self.client.sign_in(phone=settings.tg_phone, code=code)
        except SessionPasswordNeededError:
            password = input("2FA password: ").strip()
            await self.client.sign_in(password=password)

    async def is_authorized(self) -> bool:
        await self.connect()
        return await self.client.is_user_authorized()

    async def request_login_code(self, phone: str) -> str:
        await self.connect()
        sent = await self.client.send_code_request(phone)
        return sent.phone_code_hash

    async def sign_in_with_code(
        self,
        *,
        phone: str,
        code: str,
        phone_code_hash: str | None = None,
        password: str | None = None,
    ) -> None:
        await self.connect()
        try:
            await self.client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            if not password:
                raise RuntimeError("2FA_REQUIRED")
            await self.client.sign_in(password=password)

    async def list_channels(self) -> list[ChannelDTO]:
        await self.connect()
        result: list[ChannelDTO] = []
        async for dialog in self.client.iter_dialogs():
            if not dialog.is_channel:
                continue
            entity = dialog.entity
            if not isinstance(entity, TLChannel):
                continue
            result.append(
                ChannelDTO(
                    tg_id=dialog.id,
                    title=dialog.title,
                    username=getattr(entity, "username", None),
                    is_private=getattr(entity, "username", None) is None,
                )
            )
        return result

    async def resolve_channel(self, handle: str) -> ChannelDTO:
        await self.connect()
        normalized = handle.strip()
        if normalized.startswith("https://t.me/"):
            normalized = normalized.removeprefix("https://t.me/")
        normalized = normalized.lstrip("@").split("/")[0]

        entity = await self.client.get_entity(normalized)
        if not isinstance(entity, TLChannel):
            raise RuntimeError("Entity is not a channel")

        return ChannelDTO(
            tg_id=get_peer_id(entity),
            title=getattr(entity, "title", normalized),
            username=getattr(entity, "username", None),
            is_private=getattr(entity, "username", None) is None,
        )

    async def iter_messages(self, *, entity, min_id: int, limit: int | None = None):
        await self.connect()
        async for msg in self.client.iter_messages(entity, min_id=min_id, reverse=True, limit=limit):
            yield msg

    async def map_dialog_entities(self) -> dict[int, object]:
        await self.connect()
        mapping: dict[int, object] = {}
        async for dialog in self.client.iter_dialogs():
            if dialog.is_channel:
                mapping[dialog.id] = dialog.entity
        return mapping


def run(coro):
    return asyncio.run(coro)
