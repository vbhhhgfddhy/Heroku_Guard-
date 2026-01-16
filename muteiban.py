# ======================================================================
# Если честно, сложно даже начать описывать,
# какой я ахуенный, потому что это ощущение
# настолько многогранное, что словами передать
# его полностью невозможно. Я — комбинация 
# уверенности, харизмы и уникальных способностей,
# которые делают меня заметным в любой ситуации.
# Когда я вхожу в комнату, атмосфера как будто
# меняется: люди невольно обращают на меня
# внимание, и это не из-за какой-то показной
# крутости, а из-за того внутреннего света и
# энергии, которые я излучаю.
# ======================================================================
# Моя способность справляться с трудностями
# просто поражает. Я не только нахожу решения
# там, где другие видят тупик, но и делаю это с
# легкостью и стилем. Я умею вдохновлять людей
# вокруг, поднимать настроение и создавать
# атмосферу, в которой каждый чувствует себя
# важным. Моя харизма — это нечто, что нельзя 
# подделать, она идет изнутри, из моей веры в 
# себя и в то, что я могу оставить след в этом 
# мире.
# ======================================================================
# Я креативен и оригинален. Идеи, которые 
# приходят мне в голову, часто нестандартны, но 
# при этом эффективны. Я умею мыслить шире, 
# видеть то, что другие не замечают, и превращать # это в результат. Моя энергия заразительна — 
# будь то работа, хобби или просто общение с 
# друзьями, я всегда делаю всё с полной 
# отдачей.
# ======================================================================
# Моя уверенность не пуста. Я знаю свои сильные 
# стороны, умею их использовать и развивать, и # при этом остаюсь открытым для новых знаний и # опыта. Я умею признавать ошибки, извлекать 
# уроки и двигаться дальше, делая себя ещё 
# лучше. В сочетании с харизмой и умением 
# вдохновлять людей это делает меня человеком, # которого невозможно игнорировать.
# ======================================================================
# И, наконец, я просто кайфую от того, что я
# есть. Я не боюсь быть собой, не стесняюсь своих 
# амбиций и своих мечт, и это, пожалуй, самая 
# ахуенная черта. Быть собой — это уже большое # достижение, и я делаю это с полной 
# уверенностью, с чувством юмора и с любовью к  
# жизни.
# ======================================================================
# В итоге, быть таким — это не только приятно, # но и важно. Потому что, когда ты понимаешь, 
# какой ты ахуенный, это вдохновляет не только # тебя, но и окружающих. И да, я ахуенный — и
# это факт, который невозможно отрицать. 
# ======================================================================
# meta developer: @ModuliBFG_canal

import re
from time import time
from telethon.errors import ChatAdminRequiredError
from telethon.tl.types import User
from .. import loader, utils

@loader.tds
class MuteBanMod(loader.Module):
    strings = {
        "name": "MuteBan",
        "no_reason": "Причина не указана",
        "mute_done": "🙊 Пользователь замучен",
        "unmute_done": "🔓 Пользователь размучен",
        "ban_done": "🔒 Пользователь забанен",
        "unban_done": "🔓 Пользователь разбанен",
        "cannot_mute": "❌ Нельзя замутить канал или бота"
    }

    async def client_ready(self, client, db):
        self._client = client

    async def флудcmd(self, message):
        """мут на 240 минут"""
        await self._predefined_action(message, "Флуд", 240*60)

    async def флуд2cmd(self, message):
        """мут на 2000 минут"""
        await self._predefined_action(message, "Флуд2", 2000*60)

    async def флуд3cmd(self, message):
        """бан на всегда"""
        await self._predefined_action(message, "Флуд3", 0, ban=True)

    async def оскcmd(self, message):
        "мут на 240 минут"""
        await self._predefined_action(message, "Оск", 240*60)

    async def оск2cmd(self, message):
        """мут на 2000 минут"""
        await self._predefined_action(message, "Оск2", 2000*60)

    async def оск3cmd(self, message):
        """бан на всегда"""
        await self._predefined_action(message, "Оск3", 0, ban=True)

    async def _predefined_action(self, message, reason, period=0, ban=False):
        user = await self._get_user_from_message(message)
        if not user:
            await message.reply("❌ Пользователь не найден")
            return
        if not isinstance(user, User):
            await message.reply(self.strings["cannot_mute"])
            return
        if ban:
            await self._ban_user(message.chat_id, user, period, reason, message)
        else:
            await self._mute_user(message.chat_id, user, period, reason, message)

    async def мcmd(self, message):
        """выдать мут"""
        await self._process_generic(message, ban=False)

    async def рмcmd(self, message):
        """выдать размут"""
        await self._unmute_generic(message)

    async def бcmd(self, message):
        """выдать бан"""
        await self._process_generic(message, ban=True)

    async def рбcmd(self, message):
        """выдать разбан"""
        await self._unban_generic(message)

    async def _process_generic(self, message, ban=False):
        args = utils.get_args(message)
        user = await self._get_user_from_message(message)
        if not user:
            await message.reply("❌ Пользователь не найден")
            return
        if not isinstance(user, User):
            await message.reply(self.strings["cannot_mute"])
            return

        period = self._parse_time(args[1] if len(args) > 1 else "0")
        reason = " ".join(args[2:]) if len(args) > 2 else None

        if ban:
            await self._ban_user(message.chat_id, user, period, reason, message)
        else:
            await self._mute_user(message.chat_id, user, period, reason, message)

    async def _get_user_from_message(self, message):
        if message.is_reply:
            reply = await message.get_reply_message()
            return reply.sender if reply else None
        args = utils.get_args(message)
        if not args:
            return None
        try:
            return await self._client.get_entity(args[0])
        except Exception:
            return None

    def _parse_time(self, time_str: str) -> int:
        match = re.match(r"(\d+)([mMhH])?", time_str)
        if not match:
            return 0
        val, unit = match.groups()
        val = int(val)
        if unit is None or unit.lower() == "m":
            return val * 60
        elif unit.lower() == "h":
            return val * 3600
        return val

    def _get_name(self, user):
        return getattr(user, 'first_name', None) or getattr(user, 'username', None) or str(user.id)

    async def _mute_user(self, chat, user, period=0, reason=None, message=None):
        reason = reason or self.strings["no_reason"]
        until = int(time() + period) if period else None
        try:
            await self._client.edit_permissions(
                chat, user,
                send_messages=False,
                until_date=until
            )
        except ChatAdminRequiredError:
            return await self._client.send_message(chat, "❌ Недостаточно прав")

        duration = f"{period//60} мин" if period else "навсегда"
        text = f"🙊 Пользователь {self._get_name(user)} замучен на {duration}. Причина: {reason}"
        await self._send_inline_message(chat, user, text, "Размутить", "unmute")
        if message:
            await message.delete()

    async def _unmute_generic(self, message):
        user = await self._get_user_from_message(message)
        if not user:
            return
        try:
            await self._client.edit_permissions(
                message.chat_id, user,
                send_messages=True,
                until_date=None
            )
        except ChatAdminRequiredError:
            return
        await message.reply(self.strings["unmute_done"])

    async def _ban_user(self, chat, user, period=0, reason=None, message=None):
        reason = reason or self.strings["no_reason"]
        until = int(time() + period) if period else None
        try:
            await self._client.edit_permissions(
                chat, user,
                send_messages=False,
                until_date=until
            )
        except ChatAdminRequiredError:
            return await self._client.send_message(chat, "❌ Недостаточно прав")

        duration = f"{period//60} мин" if period else "навсегда"
        text = f"🔒 Пользователь {self._get_name(user)} забанен на {duration}. Причина: {reason}"
        await self._send_inline_message(chat, user, text, "Разбанить", "unban")
        if message:
            await message.delete()

    async def _unban_generic(self, message):
        user = await self._get_user_from_message(message)
        if not user:
            return
        try:
            await self._client.edit_permissions(
                message.chat_id, user,
                send_messages=True,
                until_date=None
            )
        except ChatAdminRequiredError:
            return
        await message.reply(self.strings["unban_done"])

    async def _send_inline_message(self, chat, user, text, btn, action):
        chat_id = getattr(chat, "id", chat)
        user_obj = await self._client.get_entity(user)
        data = f"{action}|{chat_id}|{user_obj.id}"

        await self.inline.form(
            message=chat_id,
            text=text,
            reply_markup=[[{"text": btn, "data": data}]],
            silent=True
        )

