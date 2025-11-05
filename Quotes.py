__version__ = (0, 0, 7)

# meta developer: https://t.me/heroku_model
# requires: pydub speechrecognition python-ffmpeg
# scope: ffmpeg

#доработанный и исправный модуль повиксели все баги.

import base64
import hashlib
import io
import os
import tempfile
import logging
from time import gmtime
from typing import List, Union

import requests
import speech_recognition as sr
from pydub import AudioSegment
import telethon
from telethon.tl import types
from telethon.tl.patched import Message
from telethon.tl.types import PeerUser, PeerChat, PeerChannel, PeerBlocked

from .. import loader, utils

logger = logging.getLogger(__name__)


# =================== UTIL CLASSES ===================

class EntityPayload:
    def __init__(self, type_: str, offset: int, length: int, **kwargs):
        self.type = type_
        self.offset = offset
        self.length = length
        self._ = kwargs

    def to_dict(self):
        return {
            "_": "MessageEntity",
            "type": self.type,
            "offset": self.offset,
            "length": self.length,
        }


class UserPayload:
    def __init__(self, id_, first_name, last_name, username, language_code, title, emoji_status, photo, type_):
        self.id = id_
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.language_code = language_code
        self.title = title
        self.emoji_status = emoji_status
        self.photo = photo
        self.type = type_
        self.name = f"{self.first_name or ''} {self.last_name or ''}"

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "username": self.username,
            "language_code": self.language_code,
            "title": self.title,
            "emoji_status": self.emoji_status,
            "photo": self.photo,
            "type": self.type,
            "name": self.name,
        }


class MessagePayload:
    def __init__(self, text, entities, chat_id, avatar, from_, reply, media=None, media_type=None, voice=None):
        self.text = text
        self.entities = entities
        self.chat_id = chat_id
        self.avatar = avatar
        self.from_ = from_
        self.reply = reply
        self.media = media
        self.media_type = media_type
        self.voice = {"waveform": voice} if voice else None

    def to_dict(self):
        return {
            "text": self.text,
            "entities": [e.to_dict() for e in self.entities] if self.entities else None,
            "chatId": self.chat_id,
            "avatar": self.avatar,
            "from": self.from_.to_dict(),
            "replyMessage": self.reply,
            "media": {"base64": self.media} if self.media else None,
            "mediaType": self.media_type,
            "voice": self.voice,
        }


class QuotePayload:
    def __init__(self, messages, type_="quote", background="#162330"):
        self.messages = messages
        self.type = type_
        self.background = background

    def to_dict(self):
        return {
            "type": self.type,
            "format": "webp",
            "width": 512,
            "height": 768,
            "scale": 2,
            "messages": [m.to_dict() for m in self.messages],
            "backgroundColor": self.background,
        }


# =================== HELPER FUNCS ===================

def strftime(time: Union[int, float]):
    t = gmtime(time)
    return (f"{t.tm_hour:02d}:" if t.tm_hour > 0 else "") + f"{t.tm_min:02d}:{t.tm_sec:02d}"


async def get_reply(message: Message):
    if reply := await message.get_reply_message():
        return {"chatId": message.chat_id, "text": reply.raw_text or "", "name": telethon.utils.get_display_name(reply.sender)}
    return None


def get_entities(entities):
    r = []
    if entities:
        for e in entities:
            ed = e.to_dict()
            type_ = ed.pop("_").replace("MessageEntity", "").lower()
            r.append(EntityPayload(type_, ed["offset"], ed["length"]))
    return r


# =================== MAIN MODULE ===================

@loader.tds
class QuotesMod(loader.Module):
    """Quotes by @vsecoder [fixed 2025]"""

    strings = {
        "name": "Quotes",
        "no_reply": "<b>[Quotes]</b> No reply",
        "api_error": "<b>[Quotes]</b> API error",
        "args_error": "<b>[Quotes]</b> Error while parsing args: <code>{}</code>",
    }

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.api_endpoint = "http://q.api.vsecoder.dev/generate"
        self.settings = self.get_settings()

    # ---------- q command ----------
    async def qcmd(self, message):
        """<reply> [count] [!rec] [!story] — create quote"""
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        if not reply:
            return await utils.answer(message, self.strings["no_reply"])

        count = next((int(a) for a in args if a.isdigit()), 1)
        recognize = "!rec" in args
        stories = "!story" in args
        bg_color = self.settings["bg_color"]

        payload = QuotePayload(
            await self.quote_parse_messages(message, count, recognize),
            "stories" if stories else "quote",
            background=bg_color,
        )
        await self.send_quote(message, payload, stories)

    # ---------- fq command ----------
    async def fqcmd(self, message):
        """<@ or id> <text> -r <@ or id> <text> ... — fake quote"""
        args = utils.get_args(message)
        msgs = await self.fake_quote_parse_messages(message)
        if not msgs:
            await utils.answer(message, self.strings["args_error"].format(args))
            return
        payload = QuotePayload(msgs, "quote", background=self.settings["bg_color"])
        await self.send_quote(message, payload)

    # ---------- sqset command ----------
    async def sqsetcmd(self, message):
        """<bg_color/max_messages> <value> — configure Quotes"""
        args = utils.get_args_raw(message).split(maxsplit=1)
        if not args or len(args) == 0:
            settings = self.settings
            return await utils.answer(
                message,
                f"<b>[Quotes]</b> Settings:\nMax messages: <code>{settings['max_messages']}</code>\nBackground: <code>{settings['bg_color']}</code>",
            )

        if args[0] == "reset":
            self.get_settings(True)
            return await utils.answer(message, "<b>[Quotes]</b> Settings reset")

        if len(args) < 2:
            return await utils.answer(message, "<b>[Quotes]</b> Not enough args")

        key, value = args
        if key not in ["bg_color", "max_messages"]:
            return await utils.answer(message, "<b>[Quotes]</b> Unknown parameter")

        if key == "max_messages":
            if not value.isdigit():
                return await utils.answer(message, "<b>[Quotes]</b> Number expected")
            value = int(value)

        self.settings[key] = value
        self.db.set("Quotes", "settings", self.settings)
        await utils.answer(message, f"<b>[Quotes]</b> {key} set to {value}")

    # ---------- helpers ----------
    def get_settings(self, force=False):
        settings = self.db.get("Quotes", "settings", {})
        if not settings or force:
            settings = {"max_messages": 15, "bg_color": "#162330"}
            self.db.set("Quotes", "settings", settings)
        return settings

    async def send_quote(self, message, payload, stories=False):
        r = await utils.run_sync(requests.post, self.api_endpoint, json=payload.to_dict())
        if r.status_code != 200:
            return await utils.answer(message, self.strings["api_error"])
        content = base64.b64decode(r.json()["image"].encode())
        img = io.BytesIO(content)
        img.name = f"Quote.{'png' if stories else 'webp'}"
        await utils.answer(message, img, force_document=stories)

    # ---------- parse messages ----------
    async def parse_messages(self, messages: List[Message]):
        payloads = []
        for msg in messages:
            text = msg.raw_text or ""
            entities = get_entities(msg.entities)
            from_ = await self.get_entity(msg)
            reply = await get_reply(msg)
            payloads.append(MessagePayload(text, entities, msg.chat_id, True, from_, reply))
        return payloads

    async def quote_parse_messages(self, message: Message, count: int, recognize=False):
        msgs = [
            m async for m in self.client.iter_messages(
                message.chat_id,
                count,
                reverse=True,
                add_offset=1,
                offset_id=(await message.get_reply_message()).id,
            )
        ]
        if len(msgs) > self.settings["max_messages"]:
            await utils.answer(message, f"<b>[Quotes]</b> Max messages = {self.settings['max_messages']}")
            return []
        return await self.parse_messages(msgs)

    async def fake_quote_parse_messages(self, message: Message):
        args = utils.get_args_raw(message).split(" -r ")
        messages = []
        for arg in args:
            if " " not in arg:
                return False
            name, text = arg.split(" ", 1)
            try:
                user = await self.client.get_entity(int(name) if name.isdigit() else name)
            except Exception:
                return False
            messages.append(
                Message(
                    id=0,
                    peer_id=message.peer_id,  # ✅ Исправлено
                    message=text,
                    from_id=user.id,
                    date=message.date,
                    out=False,
                )
            )
        return await self.parse_messages(messages)

    async def get_entity(self, message: Message) -> UserPayload:
        peer = message.from_id or message.peer_id
        entity = await self.client.get_entity(peer)
        return UserPayload(
            entity.id,
            getattr(entity, "first_name", ""),
            getattr(entity, "last_name", ""),
            getattr(entity, "username", ""),
            "ru",
            getattr(entity, "title", None),
            None,
            {"small_file_id": getattr(entity.photo, "photo_id", None)} if getattr(entity, "photo", None) else None,
            "private",
        )
