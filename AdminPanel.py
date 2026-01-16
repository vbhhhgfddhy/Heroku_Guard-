# ======================================================================
# Название модуля: [AdminPanel]
# Версия: [2.0.0]
# Описание: [админ панель для выдачи наказаний inline кнопки.]
# Автор: Heroku_Guard
# Канал и контакты: @heroku_model, https://t.me/heroku_model
# Дата создания: [07.12.2025]
# ======================================================================
#
# Лицензия: MIT License
# Copyright (c) 2025 Heroku_Guard
#
# Для подробной информации о лицензии см. файл LICENSE:
# https://raw.githubusercontent.com/vbhhhgfddhy/Heroku_model/refs/heads/main/LICENSE
#
# Эта программа предоставляется "как есть", без каких-либо гарантий, явных
# или подразумеваемых, включая, но не ограничиваясь, гарантии товарной
# пригодности и пригодности для конкретной цели. В случае возникновения
# убытков или проблем с программой, авторы или владельцы авторских прав
# не несут ответственности.
# ======================================================================

import os
import sys
import re
from datetime import datetime, timedelta
from telethon.errors import ChatAdminRequiredError
from telethon.tl.types import Message
from aiogram.types import CallbackQuery

from .. import loader, utils

BANNED_RIGHTS = {
    "view_messages": False,
    "send_messages": False,
    "send_media": False,
    "send_stickers": False,
    "send_gifs": False,
    "send_games": False,
    "send_inline": False,
}

TIME_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}

def parse_time(time_str: str) -> int:
    if time_str == "0":
        return 0
    match = re.match(r"(\d+)([smhd])", time_str.lower())
    if match:
        amount, unit = match.groups()
        return int(amount) * TIME_UNITS[unit]
    return 0

def make_link(user):
    user_id = getattr(user, "id", user)
    username = getattr(user, "username", None)
    first = getattr(user, "first_name", None)
    last = getattr(user, "last_name", None)

    if first or last:
        full = f"{first} {last}" if first and last else first or last
        return f"<a href='tg://user?id={user_id}'>{full}</a>"

    if username:
        return f"<a href='tg://user?id={user_id}'>@{username}</a>"

    return f"<a href='tg://user?id={user_id}'>ID:{user_id}</a>"

def make_warn_link(user):
    username = getattr(user, "username", None)
    user_id = getattr(user, "id", user)
    return f"https://t.me/{username}" if username else f"tg://openmessage?user_id={user_id}"

@loader.tds
class AdminPanel(loader.Module):
    strings = {
        "name": "AdminPanel",
        "no_reason": "Причина не указана",
        "mute_done": "🙊 Пользователь замучен",
        "unmute_done": "🔓 Пользователь размучен",
        "ban_done": "🔒 Пользователь забанен",
        "unban_done": "🔓 Пользователь разбанен",
        "warn_added": "⚠️ Варн выдан",
        "warn_removed": "♻️ Варн снят",
        "warn_auto_mute": "🔒 Пользователь замучен (3/3 варнов)",
        "menu_text": "Выберите действие:",
        "not_my_callback": "❌ Это не мой колбэк, игнорирую...",
        "callback_error": "❌ Ошибка в обработке кнопки",
    }

    def __init__(self):
        self._is_inline = True
        self._warns = {}

    async def client_ready(self, client, db):
        self._db = db
        self._client = client
        self._me = await client.get_me()

    async def _get_user_from_args(self, message, args):
        user_id = None

        if message.reply_to_msg_id:
            r = await message.get_reply_message()
            if r:
                user_id = r.sender_id

        if args:
            a = args[0]
            if a.isdigit():
                user_id = int(a)
                args.pop(0)
            elif a.startswith("@"):
                try:
                    ent = await self._client.get_entity(a)
                    user_id = ent.id
                    args.pop(0)
                except:
                    await message.edit(f"❌ Не удалось найти пользователя {a}")
                    return None

        if not user_id:
            await message.edit("❌ Укажите пользователя через reply, ID или @username")
            return None

        return user_id

    async def mute(self, chat, user, period=0, reason=None, message=None):
        reason = reason or self.strings["no_reason"]
        until = datetime.utcnow() + timedelta(seconds=period) if period else None

        try:
            await self._client.edit_permissions(
                chat, user,
                send_messages=False,
                send_media=False,
                send_stickers=False,
                send_gifs=False,
                send_games=False,
                send_inline=False,
                until_date=until
            )
        except ChatAdminRequiredError:
            return await self._client.send_message(chat, "❌ Недостаточно прав")

        if message:
            try: await message.delete()
            except: pass

        user_obj = await self._client.get_entity(user)
        duration = f"{period//60} мин" if period else "навсегда"

        text = f"🙊 Пользователь {make_link(user_obj)} замучен на {duration}. Причина: {reason}"
        await self._send_inline_message(chat, user, text, "Размутить", "unmute")

    async def unmute(self, chat, user, message=None):
        try:
            await self._client.edit_permissions(chat, user, send_messages=True)
        except ChatAdminRequiredError:
            return

        if message:
            try: await message.delete()
            except: pass

    async def ban(self, chat, user, period=0, reason=None, message=None):
        reason = reason or self.strings["no_reason"]
        until = datetime.utcnow() + timedelta(seconds=period) if period else None

        try:
            await self._client.edit_permissions(chat, user, **BANNED_RIGHTS, until_date=until)
        except ChatAdminRequiredError:
            return await self._client.send_message(chat, "❌ Недостаточно прав")

        if message:
            try: await message.delete()
            except: pass

        user_obj = await self._client.get_entity(user)
        duration = f"{period//3600} ч" if period else "навсегда"
        text = f"🔒 Пользователь {make_link(user_obj)} забанен на {duration}. Причина: {reason}"

        await self._send_inline_message(chat, user, text, "Разбанить", "unban")

    async def unban(self, chat, user, message=None):
        try:
            await self._client.edit_permissions(chat, user, **{k: True for k in BANNED_RIGHTS})
        except ChatAdminRequiredError:
            return

        if message:
            try: await message.delete()
            except: pass

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

    async def _send_admin_menu(self, chat_id, user_id):
        u = await self._client.get_entity(user_id)
        text = f"{self.strings['menu_text']}\n{make_link(u)}"

        buttons = [
            [{"text": "Mute", "data": f"mute_menu|{chat_id}|{user_id}"}, {"text": "Ban", "data": f"ban_menu|{chat_id}|{user_id}"}],
            [{"text": "Unmute", "data": f"unmute|{chat_id}|{user_id}"}, {"text": "Unban", "data": f"unban|{chat_id}|{user_id}"}],
            [{"text": "Warn", "data": f"warn_menu|{chat_id}|{user_id}"}],
        ]

        await self.inline.form(
            message=chat_id,
            text=text,
            reply_markup=buttons,
            silent=True
        )

    def _get_warn_list(self, chat, user):
        return self._warns.get(chat, {}).get(user, [])

    def _get_all_warns(self, chat):
        return self._warns.get(chat, {})

    def _add_warn(self, chat, user, reason="Без причины"):
        self._warns.setdefault(chat, {}).setdefault(user, []).append(reason)
        return len(self._warns[chat][user])

    def _remove_warn(self, chat, user):
        if chat in self._warns and user in self._warns[chat] and self._warns[chat][user]:
            self._warns[chat][user].pop()
            if not self._warns[chat][user]:
                del self._warns[chat][user]
            return True
        return False

    async def _warn_add_handler(self, chat, user, call=None):
        count = self._add_warn(chat, user)
        u = await self._client.get_entity(user)

        await call.answer(f"⚠️ Варн выдан ({count}/3)", show_alert=False)

        if count >= 3:
            await self.mute(chat, user, period=180 * 60, reason="3/3 варнов")
            if call and call.message:
                await call.message.edit("🔒 Пользователь автоматически замучен (3/3)", reply_markup=[])
            return

        buttons = [[
            {"text": "Выдать warn", "data": f"warn_add|{chat}|{user}"},
            {"text": "Снять warn", "data": f"warn_remove|{chat}|{user}"}
        ]]

        await call.message.edit(f"⚠️ Варн выдан ({count}/3) для {make_link(u)}", reply_markup=buttons)

    async def _warn_list_handler(self, chat, user=None, call=None):
        if user:
            warns = self._get_warn_list(chat, user)
            u = await self._client.get_entity(user)
            if warns:
                lines = "\n".join([f"{i+1}. {make_warn_link(u)} — {w}" for i, w in enumerate(warns)])
            else:
                lines = "Нет варнов"
            text = f"📋 Варны пользователя:\n{lines}"
        else:
            all_warns = self._get_all_warns(chat)
            if not all_warns:
                text = "📋 Варнов нет"
            else:
                lines = []
                for uid, warns in all_warns.items():
                    u = await self._client.get_entity(uid)
                    for i, reason in enumerate(warns, 1):
                        lines.append(f"{make_warn_link(u)} — Варн {i}: {reason}")
                text = "📋 Список всех варнов:\n" + "\n".join(lines)

        if call and call.message:
            await call.message.edit(text)
        else:
            await self.inline.form(message=chat, text=text, reply_markup=[])

    async def _handle_action(self, message, action):
        args = utils.get_args_raw(message).split()
        user = await self._get_user_from_args(message, args)
        if not user:
            return

        period = 0
        if args:
            t = parse_time(args[0])
            if t > 0:
                period = t
                args.pop(0)

        reason = " ".join(args) if args else None

        if action == "mute":
            await self.mute(message.chat_id, user, period, reason, message)
        elif action == "unmute":
            await self.unmute(message.chat_id, user, message)
        elif action == "ban":
            await self.ban(message.chat_id, user, period, reason, message)
        elif action == "unban":
            await self.unban(message.chat_id, user, message)
        elif action == "admin":
            await self._send_admin_menu(message.chat_id, user)
        elif action == "warn":
            await self._warn_list_handler(message.chat_id, user)

    @loader.command()
    async def mutecmd(self, m): await self._handle_action(m, "mute")

    @loader.command()
    async def unmutecmd(self, m): await self._handle_action(m, "unmute")

    @loader.command()
    async def bancmd(self, m): await self._handle_action(m, "ban")

    @loader.command()
    async def unbancmd(self, m): await self._handle_action(m, "unban")

    @loader.command()
    async def admincmd(self, m): await self._handle_action(m, "admin")

    @loader.command()
    async def warnlistcmd(self, m): await self._warn_list_handler(m.chat_id)

    @loader.inline_everyone
    async def actions_callback_handler(self, call: CallbackQuery):
        # Проверяем, что колбэк начинается с известных нашему модулю действий
        known_prefixes = [
            "mute_menu", "ban_menu", "mute", "ban", "unmute", "unban", 
            "admin", "warn_menu", "warn_add", "warn_remove", "warn_list"
        ]
        
        data = call.data.split("|")
        if not data:
            return
        
        # Проверяем, является ли колбэк нашим
        if data[0] not in known_prefixes:
            # Это не наш колбэк, пропускаем
            return
        
        # Теперь обрабатываем наш колбэк
        try:
            if len(data) < 3:
                await call.answer(self.strings["callback_error"], show_alert=True)
                return

            action, chat, user = data[0], int(data[1]), int(data[2])
            time_str = data[3] if len(data) == 4 else None

            if action == "mute_menu":
                buttons = [
                    [{"text": "10м", "data": f"mute|{chat}|{user}|10m"}, {"text": "30м", "data": f"mute|{chat}|{user}|30m"}],
                    [{"text": "1ч", "data": f"mute|{chat}|{user}|1h"}, {"text": "Навсегда", "data": f"mute|{chat}|{user}|0"}],
                    [{"text": "Назад", "data": f"admin|{chat}|{user}"}]
                ]
                await self.inline.form(message=chat, text="Выберите время мута", reply_markup=buttons)
                return

            elif action == "ban_menu":
                buttons = [
                    [{"text": "1д", "data": f"ban|{chat}|{user}|1d"}, {"text": "10д", "data": f"ban|{chat}|{user}|10d"}],
                    [{"text": "30д", "data": f"ban|{chat}|{user}|30d"}, {"text": "Навсегда", "data": f"ban|{chat}|{user}|0"}],
                    [{"text": "Назад", "data": f"admin|{chat}|{user}"}]
                ]
                await self.inline.form(message=chat, text="Выберите время бана", reply_markup=buttons)
                return

            elif action == "mute" and time_str is not None:
                seconds = parse_time(time_str)
                await self.mute(chat, user, seconds)
                await call.answer("🙊 Мут выдан", show_alert=False)
                return

            elif action == "ban" and time_str is not None:
                seconds = parse_time(time_str)
                await self.ban(chat, user, seconds)
                await call.answer("🔒 Бан выдан", show_alert=False)
                return

            elif action == "unmute":
                await self.unmute(chat, user)
                await call.answer("🔓 Размут выполнен", show_alert=False)
                if call.message: 
                    await call.message.edit("🔓 Пользователь размучен.", reply_markup=[])
                return

            elif action == "unban":
                await self.unban(chat, user)
                await call.answer("🔓 Разбан выполнен", show_alert=False)
                if call.message: 
                    await call.message.edit("🔓 Пользователь разбанен.", reply_markup=[])
                return

            elif action == "admin":
                await self._send_admin_menu(chat, user)
                return

            elif action == "warn_menu":
                buttons = [
                    [{"text": "Выдать warn", "data": f"warn_add|{chat}|{user}"},
                    {"text": "Снять warn", "data": f"warn_remove|{chat}|{user}"}],
                    [{"text": "Посмотреть warnlist", "data": f"warn_list|{chat}|{user}"}],
                    [{"text": "Назад", "data": f"admin|{chat}|{user}"}],
                ]
                await self.inline.form(message=chat, text="Варны:", reply_markup=buttons)
                return

            elif action == "warn_add":
                await self._warn_add_handler(chat, user, call)
                return

            elif action == "warn_remove":
                ok = self._remove_warn(chat, user)
                text = "♻️ Варн снят" if ok else "❌ Нет варнов"
                await call.answer(text, show_alert=False)

                buttons = [[
                    {"text": "Выдать warn", "data": f"warn_add|{chat}|{user}"},
                    {"text": "Снять warn", "data": f"warn_remove|{chat}|{user}"}],
                ]

                if call.message:
                    await call.message.edit(text, reply_markup=buttons)
                return

            elif action == "warn_list":
                await self._warn_list_handler(chat, user, call)
                return

        except Exception as e:
            await call.answer(f"❌ Ошибка: {str(e)[:50]}", show_alert=True)