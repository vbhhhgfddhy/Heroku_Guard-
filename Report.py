import re
from telethon import TelegramClient
from telethon.tl.custom import Message
from .. import loader, utils


@loader.tds
class ReportMod(loader.Module):
    """Модуль для репортов и логов мутов/банов с поддержкой тем"""

    strings = {
        "name": "Report",
        "report_sent": "✅ Ваш репорт отправлен на проверку.",
        "self_report": "🚫 Вы не можете отправить репорт на самого себя.",
        "chatreport_set": "✅ Чат для репортов установлен: {chat}.",
        "logsmute_set": "✅ Чат для логов мутов и банов установлен: {chat}.",
        "start_report_chat": "🛠️ Слежка за чатами включена.",
        "stop_report_chat": "🛑 Слежка за чатами выключена.",
        "invalid_chat_id": "🚫 Некорректный ID чата или ссылка.",
        "not_tracking_chat": "ℹ️ Слежка за этим чатом не была включена.",
    }

    async def client_ready(self, client: TelegramClient, db):
        self.client = client
        self.db = db

    def set(self, key, value):
        return self.db.set(self.strings("name"), key, value)

    def get(self, key, default=None):
        return self.db.get(self.strings("name"), key, default)

    def get_link(self, user):
        """Возвращает ссылку на профиль"""
        name = user.first_name or user.username or "Пользователь"
        name = utils.escape_html(name)
        return f'<a href="tg://user?id={user.id}">{name}</a>'

    async def startchatmutecmd(self, message: Message):
        """Включить слежку за репортами/мутами/банами в этом чате/теме"""
        tracked = self.get("tracked_chats", {})
        thread_id = getattr(message, "message_thread_id", None)
        tracked[str(message.chat_id)] = thread_id
        self.set("tracked_chats", tracked)

        text = "🛠️ Слежка включена"
        if thread_id:
            text += f" (тема ID {thread_id})"

        await utils.answer(message, text)

    async def stopchatmutecmd(self, message: Message):
        """Выключить слежку в этом чате/теме"""
        tracked = self.get("tracked_chats", {})
        if str(message.chat_id) not in tracked:
            return await utils.answer(message, self.strings("not_tracking_chat"))

        tracked.pop(str(message.chat_id))
        self.set("tracked_chats", tracked)
        await utils.answer(message, self.strings("stop_report_chat"))

    async def chatreportcmd(self, message: Message):
        """Установить чат/тему для репортов"""
        thread_id = getattr(message, "message_thread_id", None)
        self.set("report_chat", {
            "chat_id": message.chat_id,
            "thread_id": thread_id
        })

        chat_text = "текущий чат"
        if thread_id:
            chat_text += f" (тема ID {thread_id})"

        await utils.answer(
            message,
            self.strings("chatreport_set").format(chat=chat_text)
        )

    async def logsmutecmd(self, message: Message):
        """Установить чат/тему для логов мутов и банов"""
        thread_id = getattr(message, "message_thread_id", None)
        self.set("log_chat", {
            "chat_id": message.chat_id,
            "thread_id": thread_id
        })

        chat_text = "текущий чат"
        if thread_id:
            chat_text += f" (тема ID {thread_id})"

        await utils.answer(
            message,
            self.strings("logsmute_set").format(chat=chat_text)
        )

    @loader.watcher(out=False)
    async def watcher(self, message: Message):
        if not message.text or not message.is_group:
            return

        tracked = self.get("tracked_chats", {})
        thread_id = tracked.get(str(message.chat_id))
        message_thread_id = getattr(message, "message_thread_id", None)

        # Если чат не включён или тема не совпадает
        if str(message.chat_id) not in tracked:
            return
        if thread_id and message_thread_id != thread_id:
            return

        report_data = self.get("report_chat")
        if report_data and message.text.lower().startswith("репорт"):
            if not message.reply_to_msg_id:
                return

            report_msg = await message.get_reply_message()
            if report_msg.sender_id == message.sender_id:
                return await utils.answer(message, self.strings("self_report"))

            reporter = await self.client.get_entity(message.sender_id)
            offender = await self.client.get_entity(report_msg.sender_id)
            reason = message.text[6:].strip() or "Без причины"

            report_text = (
                "📢 <b>Новый репорт</b>\n"
                f"кто: {self.get_link(reporter)}\n"
                f"на кого: {self.get_link(offender)}\n"
                f"причина: {utils.escape_html(reason)}\n"
                f"сообщение: <a href='https://t.me/c/{str(report_msg.chat_id)[4:]}/{report_msg.id}'>ссылка</a>"
            )

            thread_id = report_data.get("thread_id")
            if thread_id:
                await self.client.send_message(
                    report_data["chat_id"],
                    report_text,
                    reply_to_msg_id=report_msg.id 
                )
            else:
                await self.client.send_message(
                    report_data["chat_id"],
                    report_text
                )
            await utils.answer(message, self.strings("report_sent"))

        log_data = self.get("log_chat")
        if not log_data:
            return

        pattern = r"^(?:/mute|мут)\s+(\d+)\s*(мин|м|ч|h|д|d|дн|days|год|y)?\s*(.*)?$"
        match = re.match(pattern, message.text.lower().strip())

        if match and message.reply_to_msg_id:
            duration_value = match.group(1)
            duration_unit = match.group(2) or ""
            reason = match.group(3).strip() if match.group(3) else "нет причины"

            moderator = await self.client.get_entity(message.sender_id)
            
            chat_permissions = await self.client.get_permissions(message.chat_id, moderator)
            if not chat_permissions.is_admin:
                # Если это не администратор, не отправляем лог
                return
            
            target_msg = await message.get_reply_message()
            target_user = await self.client.get_entity(target_msg.sender_id)

            log_text = (
                "🔇 <b>Мут</b>\n"
                f"кем: {self.get_link(moderator)}\n"
                f"кому: {self.get_link(target_user)}\n"
                f"причина: {utils.escape_html(reason)}\n"
                f"длительность: {duration_value} {duration_unit}\n"
                f"сообщение: <a href='https://t.me/c/{str(target_msg.chat_id)[4:]}/{target_msg.id}'>ссылка</a>"
            )

            thread_id = log_data.get("thread_id")
            if thread_id:
                await self.client.send_message(
                    log_data["chat_id"],
                    log_text,
                    reply_to_msg_id=target_msg.id  
                )
            else:
                await self.client.send_message(
                    log_data["chat_id"],
                    log_text
                )

