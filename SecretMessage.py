# meta developer: @xdesai

import logging
from hikkatl.tl.types import Message
from .. import loader, utils
from ..inline.types import InlineCall

@loader.tds
class SecretMessageMod(loader.Module):
    strings = {
        "name": "SecretMessage",
        "for_user_message": "🔐 Secret message for <b><a href='tg://user?id={id}'>{name}</a></b>",
        "open": "👀 Open",
        "no_user_or_message": "Specify the user and the message",
        "secret_message": "Secret message",
        "send_message": "Send secret message for {name}",
        "help_message": "<b>Usage:</b>\n<code>.с [id/username] [text]</code>\nOr reply to a user and use: <code>.с [text]</code>",
        "not_for_you": "❌ Not for you",
        "eaten": "🐈 The message was eaten by cats",
        "no_reply": "Reply to a user to send a secret message"
    }

    strings_ru = {
        "name": "SecretMessage",
        "for_user_message": "🔐 Секретное сообщение для <b><a href='tg://user?id={id}'>{name}</a></b>",
        "open": "👀 Открыть",
        "no_user_or_message": "Укажите пользователя и сообщение",
        "secret_message": "Секретное сообщение",
        "send_message": "Отправить секретное сообщение для {name}",
        "help_message": "<b>Использование:</b>\n<code>.с [id/username] [текст]</code>\nИли ответьте на сообщение: <code>.с [текст]</code>",
        "not_for_you": "❌ Не для тебя",
        "eaten": "🐈 Сообщение было съедено котами",
        "no_reply": "Ответь на сообщение, чтобы отправить секрет"
    }

    def __init__(self):
        self.config = loader.ModuleConfig()
        self._opened_messages = []

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self._tg_id = (await client.get_me()).id

    @loader.command(
        ru_doc="[id/username/reply] [текст] - Отправить секретное сообщение указанному пользователю"
    )
    async def с(self, message: Message):
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        if reply and reply.from_id:
            for_user = await self.client.get_entity(reply.from_id)
            text = args if args else reply.text
        else:
            if not args or len(args.split()) < 2:
                await utils.answer(message, self.strings("help_message"))
                return
            try:
                if args.split()[0].isdigit():
                    for_user = await self.client.get_entity(int(args.split()[0]))
                else:
                    for_user = await self.client.get_entity(args.split()[0])
                text = " ".join(args.split()[1:])
            except Exception as e:
                logging.error(f"{e}")
                await utils.answer(message, self.strings("no_user_or_message"))
                return

        if not text:
            await utils.answer(message, self.strings("no_reply"))
            return

        # изменить исходное сообщение на "..."
        if message.out:
            try:
                await message.edit("...")
            except Exception:
                pass
            await message.delete()

        await utils.answer(
            message,
            self.strings("for_user_message").format(id=for_user.id, name=for_user.first_name),
            reply_markup={
                "text": self.strings("open"),
                "callback": self._handler,
                "args": (text, for_user.id),
                "disable_security": True
            }
        )

    async def _handler(self, call: InlineCall, text: str, for_user_id: int):
        if call.from_user.id == self._tg_id:
            await call.answer(f"{text}", show_alert=True)
            return

        if call.from_user.id != for_user_id:
            await call.answer(self.strings("not_for_you"), show_alert=True)
        elif call.inline_message_id in self._opened_messages:
            await call.answer(self.strings("eaten"), show_alert=True)
        else:
            await call.answer(f"{text}", show_alert=True)
            self._opened_messages.append(call.inline_message_id)