version = (2, 0, 1)

import asyncio
import contextlib
import logging

# meta developer: https://t.me/userbothikka3

from aiogram import Bot
from hikkatl.tl.functions.channels import InviteToChannelRequest
from hikkatl.tl.types import Message, PeerUser, PeerChannel, PeerChat

from .. import loader, utils
from ..inline.types import InlineCall

logger = logging.getLogger(__name__)


class StopEvent:
    def __init__(self):
        self.state = True

    def stop(self):
        self.state = False


@loader.tds
class TagAllMod(loader.Module):
    strings = {
        "name": "TagAll",
        "bot_error": "🚫 <b>Unable to invite inline bot to chat</b>",
        "gathering": "🧚‍♀️ <b>Calling participants of this chat...</b>",
        "cancel": "🚫 Cancel",
        "cancelled": "🧚‍♀️ <b>TagAll cancelled!</b>",
        "exclude_added": "🚫 <b>User {}</b> added to exclusion list",
        "exclude_removed": "✅ <b>User {}</b> removed from exclusion list",
        "exclude_invalid": "🚫 <b>Could not find a valid user</b>",
    }

    strings_ru = {
        "bot_error": "🚫 <b>Не получилось пригласить бота в чат</b>",
        "gathering": "🧚‍♀️ <b>Отмечаю участников чата...</b>",
        "cancel": "🚫 Отмена",
        "cancelled": "🧚‍♀️ <b>Сбор участников отменен!</b>",
        "exclude_added": "🚫 <b>Пользователь {} добавлен в исключения</b>",
        "exclude_removed": "✅ <b>Пользователь {} удален из исключений</b>",
        "exclude_invalid": "🚫 <b>Не удалось найти пользователя</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("default_message", "@all", "Default message of mentions"),
            loader.ConfigValue("delete", False, "Delete messages after tagging", validator=loader.validators.Boolean()),
            loader.ConfigValue("use_bot", False, "Use inline bot to tag people", validator=loader.validators.Boolean()),
            loader.ConfigValue("timeout", 0.1, "Time interval between each tag message", validator=loader.validators.Float(minimum=0)),
            loader.ConfigValue("silent", False, "Do not send message with cancel button", validator=loader.validators.Boolean()),
            loader.ConfigValue("cycle_tagging", False, "Cycle tagging until stopped", validator=loader.validators.Boolean()),
            loader.ConfigValue("cycle_delay", 0, "Delay between cycles", validator=loader.validators.Integer(minimum=0)),
            loader.ConfigValue("exclusions", {}, "List of user IDs to exclude per chat"),
        )

    async def cancel(self, call: InlineCall, event: StopEvent):
        event.stop()
        await call.answer(self.strings("cancel"))

    @loader.command(
        groups=True,
        ru_doc="[текст] - Отметить всех участников чата",
    )
    async def tagall(self, message: Message):
        """[text] - Tag all users in chat"""
        args = utils.get_args_raw(message)
        if message.out:
            await message.delete()

        if self.config["use_bot"]:
            try:
                await self._client(InviteToChannelRequest(message.peer_id, [self.inline.bot_username]))
            except Exception:
                await utils.answer(message, self.strings("bot_error"))
                return
            with contextlib.suppress(Exception):
                Bot.set_instance(self.inline.bot)
            chat_id = int(f"-100{utils.get_chat_id(message)}")
        else:
            chat_id = utils.get_chat_id(message)

        event = StopEvent()

        if not self.config["silent"]:
            cancel = await self.inline.form(
                message=message,
                text=self.strings("gathering"),
                reply_markup={"text": self.strings("cancel"), "callback": self.cancel, "args": (event,)},
            )

        first, br = True, False
        while True if self.config["cycle_tagging"] else first:
            for chunk in utils.chunks(
                [
                    f'<a href="tg://user?id={user.id}">\xad</a>'
                    async for user in self._client.iter_participants(message.peer_id)
                    if str(user.id) not in self.config["exclusions"].get(str(chat_id), {})
                ],
                5,
            ):
                m = await (
                    self.inline.bot.send_message
                    if self.config["use_bot"]
                    else self._client.send_message
                )(
                    chat_id,
                    utils.escape_html(args or self.config["default_message"]) + "\xad".join(chunk),
                )

                if self.config["delete"]:
                    with contextlib.suppress(Exception):
                        await m.delete()

                async def _task():
                    if self.config["silent"]:
                        return
                    while True:
                        if not event.state:
                            await cancel.edit(self.strings("cancelled"))
                            return
                        await asyncio.sleep(0.1)

                task = asyncio.ensure_future(_task())
                await asyncio.sleep(self.config["timeout"])
                task.cancel()
                if not event.state:
                    br = True
                    break

            if br:
                break

            first = False
            if self.config["cycle_tagging"]:
                await asyncio.sleep(self.config["cycle_delay"])

        if not self.config["silent"]:
            await cancel.delete()

    @loader.command(
        groups=True,
        ru_doc="- <reply/id/username> — добавить/удалить пользователя из исключений тегов ",
    )
    async def tagexclude(self, message: Message):
        """Add/remove user from tag exclusions (reply or by id/username)"""
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        user = None

        if reply and reply.from_id:
            user = reply.from_id
        elif args:
            try:
                if args[0].isdigit():
                    user = int(args[0])
                else:
                    user_obj = await self._client.get_entity(args[0])
                    user = user_obj.id
            except Exception:
                await utils.answer(message, self.strings("exclude_invalid"))
                return
        else:
            await utils.answer(message, self.strings("exclude_invalid"))
            return

        chat_id = str(utils.get_chat_id(message))
        user_id = str(user)

        if chat_id not in self.config["exclusions"]:
            self.config["exclusions"][chat_id] = {}

        if user_id in self.config["exclusions"][chat_id]:
            del self.config["exclusions"][chat_id][user_id]
            await utils.answer(message, self.strings("exclude_removed").format(user_id))
        else:
            self.config["exclusions"][chat_id][user_id] = True
            await utils.answer(message, self.strings("exclude_added").format(user_id))