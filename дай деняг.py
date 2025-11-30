import asyncio
import datetime
from .. import loader, utils

# meta developer: https://t.me/heroku_model

@loader.tds
class DailyReplyMod(loader.Module):
    """Модуль ответа на заданную команду раз в день и управление черным списком"""

    strings = {"name": "дай деняг"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "command",
                "дай деняг",
                "Команда, на которую будет отвечать бот."
            )
        )

    async def client_ready(self, _, db):
        self.db = db
        self.loop = asyncio.get_event_loop()

        if self.db.get("DailyReply", "dailyreply_enabled_chats") is None:
            self.db.set("DailyReply", "dailyreply_enabled_chats", [])
        if self.db.get("DailyReply", "dailyreply_users") is None:
            self.db.set("DailyReply", "dailyreply_users", {})
        if self.db.get("DailyReply", "dailyreply_beggars") is None:
            self.db.set("DailyReply", "dailyreply_beggars", {})

        self.loop.create_task(self.schedule_daily_reset())

    async def schedule_daily_reset(self):
        while True:
            now_utc = datetime.datetime.utcnow()
            msktime = datetime.time(12, 0, 0, tzinfo=datetime.timezone.utc)
            next_reset_time = datetime.datetime.combine(now_utc.date(), msktime) + datetime.timedelta(days=1)
            wait_time = (next_reset_time - now_utc).total_seconds()
            await asyncio.sleep(wait_time)
            await self.reset_daily_counts()

    async def reset_daily_counts(self):
        users = self.db.get("DailyReply", "dailyreply_users", {})
        for chat_id, chat_users in users.items():
            for user_id, data in chat_users.items():
                data['count'] = 0
                data['last_reset'] = datetime.datetime.utcnow().replace(microsecond=0).isoformat()
        self.db.set("DailyReply", "dailyreply_users", users)

    async def startchatcmd(self, message):
        """Включить модуль реакции на команду в текущем чате."""
        chat_id = str(message.chat_id)
        enabled_chats = self.db.get("DailyReply", "dailyreply_enabled_chats", [])
        if chat_id in enabled_chats:
            await message.edit("<b>Модуль уже включён в этом чате.</b>")
            return
        enabled_chats.append(chat_id)
        self.db.set("DailyReply", "dailyreply_enabled_chats", enabled_chats)
        await message.edit("<b>Модуль реакции включён в этом чате.</b>")

    async def stopchatcmd(self, message):
        """Выключить модуль реакции на команду в текущем чате."""
        chat_id = str(message.chat_id)
        enabled_chats = self.db.get("DailyReply", "dailyreply_enabled_chats", [])
        if chat_id not in enabled_chats:
            await message.edit("<b>Модуль не был включён в этом чате.</b>")
            return
        enabled_chats.remove(chat_id)
        self.db.set("DailyReply", "dailyreply_enabled_chats", enabled_chats)
        await message.edit("<b>Модуль реакции выключен в этом чате.</b>")

    @loader.command(name="list")
    async def listcmd(self, message):
        """Показать пользователей, писавших заданную команду за сутки раз."""
        chat_id = str(message.chat_id)
        users = self.db.get("DailyReply", "dailyreply_users", {})
        chat_users = users.get(chat_id, {})

        if not chat_users:
            await message.reply("<b>Пока никто в этом чате не писал заданную команду.</b>")
            return

        now_utc = datetime.datetime.utcnow()
        msg_lines = [f"<b>Пользователи, писавшие '{self.config['command']}' за сутки раз:</b>"]

        sorted_users = sorted(chat_users.items(), key=lambda item: item[1]['count'], reverse=True)

        for index, (user_id, data) in enumerate(sorted_users, 1):
            if not isinstance(data, dict):
                continue
            count = data.get('count', 0)
            last_reset = data.get('last_reset', None)

            if not last_reset:
                continue

            try:
                last_time = datetime.datetime.strptime(last_reset, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                last_time = None

            if last_time and (now_utc - last_time) < datetime.timedelta(days=1):
                try:
                    user = await message.client.get_entity(int(user_id))
                    username = getattr(user, "username", None)
                    if username:
                        username_link = f"t.me/{username}"
                    else:
                        username_link = f"tg://openmessage?user_id={user_id}"
                except:
                    username_link = f"tg://openmessage?user_id={user_id}"

                msg_lines.append(f"{index}. {username_link} — {count} раз")

        next_reset_time = datetime.datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        msg_lines.append(f"\n<b>Обновление списка через:</b> {str(next_reset_time - datetime.datetime.utcnow()).split('.')[0]}")

        await message.reply("\n".join(msg_lines))

    @loader.command(name="beggars")
    async def beggarscmd(self, message):
        """Добавить или удалить пользователя из черного списка (на ответ заданной командой)."""
        chat_id = str(message.chat_id)

        if not message.reply_to_msg_id:
            await message.reply("Пожалуйста, ответьте на сообщение пользователя, чтобы управлять черным списком.")
            return

        reply_msg = await message.client.get_messages(message.chat_id, ids=message.reply_to_msg_id)
        if not reply_msg or not reply_msg.sender:
            await message.reply("Не удалось определить пользователя из этого сообщения.")
            return

        user = reply_msg.sender
        user_id = str(user.id)

        beggars = self.db.get("DailyReply", "dailyreply_beggars", {})
        chat_beggars = set(beggars.get(chat_id, []))

        if user_id in chat_beggars:
            chat_beggars.remove(user_id)
            await message.reply("Пользователь удалён из черного списка.")
        else:
            chat_beggars.add(user_id)
            await message.reply("Пользователь добавлен в черный список.")

        beggars[chat_id] = list(chat_beggars)
        self.db.set("DailyReply", "dailyreply_beggars", beggars)

    @loader.command(name="listwps")
    async def listwpscmd(self, message):
        """Показать список пользователей в черном списке для текущего чата."""
        chat_id = str(message.chat_id)
        beggars = self.db.get("DailyReply", "dailyreply_beggars", {})
        chat_beggars = beggars.get(chat_id, [])
        if not chat_beggars:
            await message.reply("В черном списке нет ни одного пользователя.")
            return
        
        names = []
        for index, user_id in enumerate(chat_beggars, 1):
            try:
                user = await message.client.get_entity(int(user_id))
                username = getattr(user, "username", None)
                if username:
                    username_link = f"t.me/{username}"
                else:
                    username_link = f"tg://openmessage?user_id={user_id}"
                names.append(f"{index}. {username_link}")
            except:
                names.append(f"{index}. tg://openmessage?user_id={user_id}")

        await message.reply("Черный список:\n" + "\n".join(names))

    @loader.command(name="updatelist")
    async def updatelistcmd(self, message):
        """Обнуляет список участников для возможности снова писать заданную команду."""
        self.db.set("DailyReply", "dailyreply_users", {})
        await message.reply("Список участников сброшен. Теперь пользователи могут снова писать заданную команду.")

    @loader.watcher(out=False)
    async def watcher(self, message):
        if not message.text:
            return

        chat_id = str(message.chat_id)
        enabled_chats = self.db.get("DailyReply", "dailyreply_enabled_chats", [])
        if chat_id not in enabled_chats:
            return

        text = message.text.strip().lower()
        command = self.config["command"].lower()

        if text == "лист":
            return await self.listcmd(message)

        if text != command:
            return

        user_id = str(message.sender_id)

        beggars = self.db.get("DailyReply", "dailyreply_beggars", {})
        chat_beggars = set(beggars.get(chat_id, []))
        if user_id in chat_beggars:
            return

        users = self.db.get("DailyReply", "dailyreply_users", {})
        chat_users = users.get(chat_id, {})

        now_utc = datetime.datetime.utcnow()

        if user_id in chat_users:
            chat_users[user_id]['count'] += 1
        else:
            chat_users[user_id] = {'count': 1, 'last_reset': now_utc.replace(microsecond=0).isoformat()}

        users[chat_id] = chat_users
        self.db.set("DailyReply", "dailyreply_users", users)

        await message.reply("дать 1e21")
