___version 01.1.1)___


# ======================================================================
# Название модуля: [DailyReplyMod]
# Версия: [01.1.1]
# Описание: [Модуль для бфг бота.]
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
# meta developer: @heroku_model

import os
import sys
import asyncio
import datetime
from .. import loader, utils

@loader.tds
class DailyReplyMod(loader.Module):
    """Модуль реакции на команду с кулдауном, предупреждениями и черным списком"""

    strings = {"name": "дай деняг"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "commands",
                ["дай деняг", "дай денег", "дейте деняг", "дайте денег", "я хуесос"],
                "Список команд, на которые бот будет реагировать."
            ),
            loader.ConfigValue("daily_reply_text", "дать 1e21", "Текст ответа на команду."),
            loader.ConfigValue("cooldown_minutes", 60, "Кулдаун между использованими команды (в минутах)."),
            loader.ConfigValue("autoban_minutes", 300, "Время автоматического бана при повторном нарушении после предупреждения (в минутах)."),
            loader.ConfigValue("auto_reset_days", 7, "Через сколько дней автоматически сбрасывать список лист."),
            loader.ConfigValue("max_weekly_messages", 10, "Количество сообщений, после которого приходит предупреждение.")
        )

    async def client_ready(self, client, db):
        self.db = db
        self.client = client
        self.loop = asyncio.get_event_loop()

        if self.db.get("DailyReply", "dailyreply_enabled_chats") is None:
            self.db.set("DailyReply", "dailyreply_enabled_chats", [])
        if self.db.get("DailyReply", "dailyreply_users") is None:
            self.db.set("DailyReply", "dailyreply_users", {})
        if self.db.get("DailyReply", "dailyreply_beggars") is None:
            self.db.set("DailyReply", "dailyreply_beggars", {})
        if self.db.get("DailyReply", "last_reset") is None:
            self.db.set("DailyReply", "last_reset", datetime.datetime.utcnow().isoformat())

        self.loop.create_task(self.schedule_auto_reset())
        self.loop.create_task(self.auto_unban_task())

    async def schedule_auto_reset(self):
        while True:
            last_reset_str = self.db.get("DailyReply", "last_reset")
            last_reset = datetime.datetime.fromisoformat(last_reset_str)
            days = int(self.config["auto_reset_days"])
            next_reset = last_reset + datetime.timedelta(days=days)
            wait_time = (next_reset - datetime.datetime.utcnow()).total_seconds()
            if wait_time < 0:
                wait_time = 60  # на случай, если время уже прошло
            await asyncio.sleep(wait_time)
            self.db.set("DailyReply", "dailyreply_users", {})
            self.db.set("DailyReply", "last_reset", datetime.datetime.utcnow().isoformat())

    async def auto_unban_task(self):
        while True:
            await asyncio.sleep(60)
            now = datetime.datetime.utcnow()
            beggars = self.db.get("DailyReply", "dailyreply_beggars", {})
            users = self.db.get("DailyReply", "dailyreply_users", {})

            for chat_id, chat_users in users.items():
                chat_beggars = set(beggars.get(chat_id, []))
                updated = False
                for user_id, data in chat_users.items():
                    ban_until_str = data.get("ban_until")
                    if ban_until_str:
                        ban_until = datetime.datetime.fromisoformat(ban_until_str)
                        if now >= ban_until and user_id in chat_beggars:
                            chat_beggars.remove(user_id)
                            data["ban_until"] = None
                            updated = True
                            try:
                                entity = await self.client.get_entity(int(user_id))
                                username = f"@{entity.username}" if entity.username else f"[{entity.first_name}](tg://openmessage?user_id={user_id})"
                            except:
                                username = f"[{user_id}](tg://openmessage?user_id={user_id})"
                            await self.client.send_message(
                                int(chat_id),
                                f"{username} ✅ Ваш доступ к команде снова открыт. Пользуйтесь аккуратно!"
                            )
                if updated:
                    beggars[chat_id] = list(chat_beggars)
                    self.db.set("DailyReply", "dailyreply_beggars", beggars)
                    self.db.set("DailyReply", "dailyreply_users", users)

    async def startchatcmd(self, message):
        """Включить модуль реакции на команду в текущем чате."""
        chat_id = str(message.chat_id)
        enabled = self.db.get("DailyReply", "dailyreply_enabled_chats", [])
        if chat_id in enabled:
            return await message.edit("<b>Модуль уже включён в этом чате.</b>")
        enabled.append(chat_id)
        self.db.set("DailyReply", "dailyreply_enabled_chats", enabled)
        await message.edit("<b>Модуль включён в этом чате.</b>")

    async def stopchatcmd(self, message):
        """Выключить модуль реакции на команду в текущем чате."""
        chat_id = str(message.chat_id)
        enabled = self.db.get("DailyReply", "dailyreply_enabled_chats", [])
        if chat_id not in enabled:
            return await message.edit("<b>Модуль не был включён в этом чате.</b>")
        enabled.remove(chat_id)
        self.db.set("DailyReply", "dailyreply_enabled_chats", enabled)
        await message.edit("<b>Модуль выключен в этом чате.</b>")

    @loader.command(name="list")
    async def listcmd(self, message):
        """Показать пользователей, писавших команду за неделю."""
        chat_id = str(message.chat_id)
        users = self.db.get("DailyReply", "dailyreply_users", {})
        chat_users = users.get(chat_id, {})
        if not chat_users:
            return await message.reply("<b>Пока никто в этом чате не писал команду.</b>")

        msg_lines = [f"<b>Пользователи, писавшие команды:</b>"]
        sorted_users = sorted(chat_users.items(), key=lambda x: x[1]["count"], reverse=True)

        for i, (user_id, data) in enumerate(sorted_users, 1):
            count = data.get("count", 0)
            ban_until_str = data.get("ban_until")
            ban_info = ""
            if ban_until_str:
                ban_until = datetime.datetime.fromisoformat(ban_until_str)
                remaining = ban_until - datetime.datetime.utcnow()
                if remaining.total_seconds() > 0:
                    h, m, s = remaining.seconds // 3600, (remaining.seconds % 3600) // 60, remaining.seconds % 60
                    ban_info = f" — забанен ещё {h}ч {m}м {s}с"
            try:
                user = await message.client.get_entity(int(user_id))
                link = f"t.me/{user.username}" if user.username else f"tg://openmessage?user_id={user_id}"
            except:
                link = f"tg://openmessage?user_id={user_id}"
            msg_lines.append(f"{i}. {link} — {count} раз{ban_info}")

        last_reset_str = self.db.get("DailyReply", "last_reset")
        last_reset = datetime.datetime.fromisoformat(last_reset_str)
        days = int(self.config["auto_reset_days"])
        next_reset = last_reset + datetime.timedelta(days=days)
        delta = next_reset - datetime.datetime.utcnow()
        msg_lines.append(f"\n<b>Обновление списка через:</b> {str(delta).split('.')[0]}")
        await message.reply("\n".join(msg_lines))

    @loader.command(name="updatelist")
    async def updatelistcmd(self, message):
        """Полностью сбрасывает список участников в каждом чате."""
        self.db.set("DailyReply", "dailyreply_users", {})
        self.db.set("DailyReply", "last_reset", datetime.datetime.utcnow().isoformat())
        await message.reply("Список участников полностью сброшен.")

    @loader.command(name="beggars")
    async def beggarscmd(self, message):
        """Добавить или удалить пользователя из чёрного списка (ответом на сообщение)."""
        chat_id = str(message.chat_id)
        if not message.reply_to_msg_id:
            return await message.reply("Ответьте на сообщение пользователя.")

        reply_msg = await message.client.get_messages(message.chat_id, ids=message.reply_to_msg_id)
        if not reply_msg or not reply_msg.sender:
            return await message.reply("Не удалось определить пользователя.")

        user_id = str(reply_msg.sender.id)
        beggars = self.db.get("DailyReply", "dailyreply_beggars", {})
        chat_beggars = set(beggars.get(chat_id, []))

        if user_id in chat_beggars:
            chat_beggars.remove(user_id)
            await message.reply("Пользователь удалён из чёрного списка.")
        else:
            chat_beggars.add(user_id)
            await message.reply("Пользователь добавлен в чёрный список.")

        beggars[chat_id] = list(chat_beggars)
        self.db.set("DailyReply", "dailyreply_beggars", beggars)

    @loader.command(name="listwps")
    async def listwpscmd(self, message):
        """Показать список пользователей в чёрном списке в текущем чате с оставшимся временем бана."""
        chat_id = str(message.chat_id)
        beggars = self.db.get("DailyReply", "dailyreply_beggars", {})
        chat_beggars = beggars.get(chat_id, [])
        if not chat_beggars:
            return await message.reply("В чёрном списке нет ни одного пользователя.")

        lines = []
        users = self.db.get("DailyReply", "dailyreply_users", {})
        chat_users = users.get(chat_id, {})
        for i, user_id in enumerate(chat_beggars, 1):
            data = chat_users.get(user_id, {})
            ban_until_str = data.get("ban_until")
            ban_info = ""
            if ban_until_str:
                now = datetime.datetime.utcnow()
                ban_until = datetime.datetime.fromisoformat(ban_until_str)
                remaining = ban_until - now
                if remaining.total_seconds() > 0:
                    h, m, s = remaining.seconds // 3600, (remaining.seconds % 3600) // 60, remaining.seconds % 60
                    ban_info = f" — бан ещё {h}ч {m}м {s}с"
            try:
                u = await message.client.get_entity(int(user_id))
                link = f"t.me/{u.username}" if u.username else f"tg://openmessage?user_id={user_id}"
            except:
                link = f"tg://openmessage?user_id={user_id}"
            lines.append(f"{i}. {link}{ban_info}")

        await message.reply("Черный список:\n" + "\n".join(lines))

    @loader.watcher(out=False)
    async def watcher(self, message):
        if not message.text:
            return

        chat_id = str(message.chat_id)
        enabled = self.db.get("DailyReply", "dailyreply_enabled_chats", [])
        if chat_id not in enabled:
            return

        text = message.text.strip().lower()
        commands = [c.lower() for c in self.config["commands"]]
        if text == "лист":
            return await self.listcmd(message)
        if text not in commands:
            return

        user_id = str(message.sender_id)
        beggars = self.db.get("DailyReply", "dailyreply_beggars", {})
        chat_beggars = set(beggars.get(chat_id, []))
        if user_id in chat_beggars:
            return await message.reply(
                f"⛔ Вы находитесь в чёрном списке команды.\n"
                f"Чтобы снять ограничения, напишите: https://t.me/Heroku_Guard_feedback_bot?start"
            )

        users = self.db.get("DailyReply", "dailyreply_users", {})
        if chat_id not in users:
            users[chat_id] = {}
        chat_users = users[chat_id]
        now = datetime.datetime.utcnow()

        cooldown_minutes = int(self.config["cooldown_minutes"])
        cooldown = cooldown_minutes * 60
        if user_id in chat_users:
            last_use_str = chat_users[user_id].get("last_use")
            if last_use_str:
                last_use = datetime.datetime.fromisoformat(last_use_str)
                diff = (now - last_use).total_seconds()
                if diff < cooldown:
                    remaining = cooldown - diff
                    minutes = int(remaining // 60)
                    if minutes < 1:
                        minutes = 1
                    return await message.reply(
                        f"⛔ На данную команду установлено ограничение: <b>{cooldown_minutes} минут</b>.\n"
                        f"Повторите попытку через <b>{minutes} минут</b>."
                    )

        if user_id in chat_users:
            chat_users[user_id]["count"] += 1
        else:
            chat_users[user_id] = {
                "count": 1,
                "last_reset": now.replace(microsecond=0).isoformat(),
                "warned": False,
                "ban_until": None
            }
        chat_users[user_id]["last_use"] = now.replace(microsecond=0).isoformat()

        max_msgs = int(self.config["max_weekly_messages"])
        if chat_users[user_id]["count"] > max_msgs:
            if not chat_users[user_id].get("warned", False):
                chat_users[user_id]["warned"] = True
                await message.reply(
                    f"⚠️ <b>Предупреждение!</b>\n"
                    f"Вы написали более {max_msgs} раз команду за неделю.\n"
                    "Прекратите использовать команду до обновления списка, иначе я буду вынужден добавить вас в чёрный список команды."
                )
            else:
                ban_minutes = int(self.config["autoban_minutes"])
                ban_until = now + datetime.timedelta(minutes=ban_minutes)
                chat_users[user_id]["ban_until"] = ban_until.replace(microsecond=0).isoformat()
                chat_beggars.add(user_id)
                beggars[chat_id] = list(chat_beggars)
                self.db.set("DailyReply", "dailyreply_beggars", beggars)
                return await message.reply(
                    f"⛔ Вы повторно нарушили правило!\n"
                    f"Вы добавлены в чёрный список команды на <b>{ban_minutes} минут</b>."
                )

        users[chat_id] = chat_users
        self.db.set("DailyReply", "dailyreply_users", users)

        reply_text = self.config["daily_reply_text"]
        await message.reply(reply_text)
