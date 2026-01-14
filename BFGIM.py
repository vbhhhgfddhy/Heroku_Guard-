from telethon.tl.types import Message
from ..inline.types import InlineCall
from .. import loader, utils
import asyncio
import re

@loader.tds
class BFGIM(loader.Module):
    """инлайн менеджер для BFG. by @codermasochist"""

    strings = {"name": "BFGIM"}
    _bot = "@bforgame_bot"

    @loader.command()
    async def ccmd(self, message: Message):
        """— <reply/id> - oткрыть меню"""
        args = utils.get_args(message)
        user_id = None

        if not args:
            if message.is_reply:
                reply = await message.get_reply_message()
                user_id = reply.sender_id
            else:
                await utils.answer(message, "реплай или айди.")
                return
        else:
            user = args[0]
            if user.isdigit():
                user_id = int(user)
            else:
                try:
                    user = await self.client.get_entity(user)
                    user_id = user.id
                except Exception:
                    await utils.answer(message, "ошибочке пум пум пум")
                    return

        await self.show_main_menu(message, user_id, is_inline=False)

    async def show_main_menu(self, call, user_id, is_inline=True):
        buttons = [
            [
                {"text": "профиль", "callback": self.profile, "args": (user_id,)},
                {"text": "чс", "callback": self.check_chs, "args": (user_id,)}
            ],
            [
                {"text": "клан", "callback": self.invite_menu, "args": (user_id,)},
                {"text": "узнать ид", "callback": self.get_ids, "args": (user_id,)}
            ],
            [{"text": "закрыть", "callback": self.close_menu}]
        ]

        text = f"<b>выберите для игрока:</b>\n<code>{user_id}</code>"

        if is_inline:
            await call.edit(text, reply_markup=buttons)
        else:
            await self.inline.form(text, message=call, reply_markup=buttons)

    async def execute_command(self, command: str) -> str:
        async with self.client.conversation(self._bot) as conv:
            try:
                await conv.send_message(command)
                return (await conv.get_response(timeout=10)).raw_text
            except asyncio.TimeoutError:
                return "бот не ответил :("

    async def profile(self, call: InlineCall, user_id):
        result = await self.execute_command(f"профиль {user_id}")
        await self.show_result(call, user_id, result)

    async def check_chs(self, call: InlineCall, user_id):
        result = await self.execute_command(f"информация о чс {user_id}")
        await self.show_result(call, user_id, result)

    async def invite_menu(self, call: InlineCall, user_id):
        buttons = [
            [{"text": "пригласить", "callback": self.invite, "args": (user_id,)}],
            [{"text": "исключить", "callback": self.kick, "args": (user_id,)}],
            [{"text": "назад", "callback": self.show_main_menu, "args": (user_id,)}]
        ]
        await call.edit("<b>че будем с ним делать?)</b>", reply_markup=buttons)

    async def invite(self, call: InlineCall, user_id):
        bfg_id = await self.get_bfg_id(user_id)
        if not bfg_id:
            await call.edit("не смог получить ид бфг.")
            return

        result = await self.execute_command(f"клан пригласить {bfg_id}")
        await self.show_result(call, user_id, result, back_callback=self.invite_menu)

    async def kick(self, call: InlineCall, user_id):
        bfg_id = await self.get_bfg_id(user_id)
        if not bfg_id:
            await call.edit("иди нахуй")
            return

        result = await self.execute_command(f"клан исключить {bfg_id}")
        await self.show_result(call, user_id, result, back_callback=self.invite_menu)

    async def get_bfg_id(self, user_id):
        profile_data = await self.execute_command(f"профиль {user_id}")
        match = re.search(r"🪪 ID: (\d+)", profile_data)
        return match.group(1) if match else None

    async def get_ids(self, call: InlineCall, user_id):
        bfg_id = await self.get_bfg_id(user_id) or "не найден"
        text = f"<b>Telegram ID:</b> <code>{user_id}</code>\n\n<b>BFG ID:</b> <code>{bfg_id}</code>"
        buttons = [[{"text": "назад", "callback": self.show_main_menu, "args": (user_id,)}]]
        await call.edit(text, reply_markup=buttons)

    async def close_menu(self, call: InlineCall):
        await call.delete()

    async def show_result(self, call: InlineCall, user_id, result, back_callback=None):
        back_btn = [{"text": "назад", "callback": back_callback, "args": (user_id,)}] if back_callback else \
                  [{"text": "назад", "callback": self.show_main_menu, "args": (user_id,)}]
        await call.edit(f"<b>Результат:</b>\n\n{result}", reply_markup=[back_btn])


    @loader.command()
    async def профиль(self, message: Message):
        """Показывает профиль игрока."""
        args = utils.get_args(message)
        
        # Проверяем, если аргументы пустые
        if not args:
            # Если это ответ на сообщение, берем sender_id
            if message.is_reply:
                reply = await message.get_reply_message()
                user_id = reply.sender_id
            else:
                await utils.answer(message, "Укажите ID пользователя или ответьте на его сообщение.")
                return
        else:
            user_id = args[0] if args[0].isdigit() else None
            if not user_id:
                await utils.answer(message, "Укажите правильный ID пользователя.")
                return

        result = await self.execute_command(f"профиль {user_id}")
        await utils.answer(message, f"Профиль пользователя {user_id}:\n\n{result}")

    @loader.command()
    async def чс(self, message: Message):
        """Показывает информацию о черном списке пользователя."""
        args = utils.get_args(message)
        
        if not args:
            if message.is_reply:
                reply = await message.get_reply_message()
                user_id = reply.sender_id
            else:
                await utils.answer(message, "Укажите ID пользователя или ответьте на его сообщение.")
                return
        else:
            user_id = args[0] if args[0].isdigit() else None
            if not user_id:
                await utils.answer(message, "Укажите правильный ID пользователя.")
                return

        result = await self.execute_command(f"информация о чс {user_id}")
        await utils.answer(message, f"Информация о чс для пользователя {user_id}:\n\n{result}")

    @loader.command()
    async def пригласить(self, message: Message):
        """Приглашает пользователя в клан."""
        args = utils.get_args(message)
        
        if not args:
            if message.is_reply:
                reply = await message.get_reply_message()
                user_id = reply.sender_id
            else:
                await utils.answer(message, "Укажите ID пользователя или ответьте на его сообщение.")
                return
        else:
            user_id = args[0] if args[0].isdigit() else None
            if not user_id:
                await utils.answer(message, "Укажите правильный ID пользователя.")
                return

        bfg_id = await self.get_bfg_id(user_id)
        if not bfg_id:
            await utils.answer(message, f"Не удалось получить BFG ID для пользователя {user_id}.")
            return

        result = await self.execute_command(f"клан пригласить {bfg_id}")
        await utils.answer(message, f"Результат приглашения игрока {user_id} в клан:\n\n{result}")

    @loader.command()
    async def кик(self, message: Message):
        """Исключает пользователя из клана."""
        args = utils.get_args(message)
        
        if not args:
            if message.is_reply:
                reply = await message.get_reply_message()
                user_id = reply.sender_id
            else:
                await utils.answer(message, "Укажите ID пользователя или ответьте на его сообщение.")
                return
        else:
            user_id = args[0] if args[0].isdigit() else None
            if not user_id:
                await utils.answer(message, "Укажите правильный ID пользователя.")
                return

        bfg_id = await self.get_bfg_id(user_id)
        if not bfg_id:
            await utils.answer(message, f"Не удалось получить BFG ID для пользователя {user_id}.")
            return

        result = await self.execute_command(f"клан исключить {bfg_id}")
        await utils.answer(message, f"Результат исключения игрока {user_id} из клана:\n\n{result}")

    @loader.command()
    async def ид(self, message: Message):
        """Получает ID пользователя в BFG и Telegram."""
        args = utils.get_args(message)
        
        if not args:
            if message.is_reply:
                reply = await message.get_reply_message()
                user_id = reply.sender_id
            else:
                await utils.answer(message, "Укажите ID пользователя или ответьте на его сообщение.")
                return
        else:
            user_id = args[0] if args[0].isdigit() else None
            if not user_id:
                await utils.answer(message, "Укажите правильный ID пользователя.")
                return

        bfg_id = await self.get_bfg_id(user_id) or "не найден"
        text = f"<b>Telegram ID:</b> <code>{user_id}</code>\n\n<b>BFG ID:</b> <code>{bfg_id}</code>"
        await utils.answer(message, text)
