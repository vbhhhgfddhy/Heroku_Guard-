__version__ = (1, 0, 0)

#  ======================================================================
# Название модуля: [DailyReplyMod]
# Версия: [1.0.0]
# Описание: [Модуль для рассылки клановый афиши в бфг чатах.]
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
import logging
from datetime import datetime, timedelta, timezone

from telethon.tl.types import Message
from .. import loader, utils

logger = logging.getLogger(__name__)

MSK = timezone(timedelta(hours=3))


@loader.tds
class ClanAdvertMod(loader.Module):
    """
    Автоматическая рассылка афиши в двух чатах
    (разные интервалы, автозапуск, лог, очистка логов)
    """

    strings = {
        "name": "Clan",
        "enabled": (
            "✅ <b>Модуль Clan включён</b>\n\n"
            "Чат 1: {}\n"
            "Чат 2: {}"
        ),
        "disabled": "⛔ <b>Модуль Clan выключен</b>",
        "log_title": "📊 <b>Лог афиши (последние 20)</b>\n\n",
        "log_empty": "Лог пуст.",
        "logs_cleared": "🗑 <b>Логи афиши очищены</b>",
        "all_cleared": "🗑 <b>Все данные сброшены (включая логи и таймеры)</b>"
    }

    config = loader.ModuleConfig(
        loader.ConfigValue(
            "interval1",
            15,
            "КД для 1 чата (в минутах)",
            validator=loader.validators.Integer(minimum=1),
        ),
        loader.ConfigValue("chat1", "None", "Чат №1"),
        loader.ConfigValue("chat2", "None", "Чат №2"),
        loader.ConfigValue("text1", "идёт набор в клан", "Текст для чата №1"),
        loader.ConfigValue("text2", "идёт наоборот в клан", "Текст для чата №2"),
        loader.ConfigValue("photo1", "None", "Фото для чата №1"),
        loader.ConfigValue("photo2", "None", "Фото для чата №2"),
        loader.ConfigValue(
            "interval2",
            15,
            "КД для 2 чата (в минутах)",
            validator=loader.validators.Integer(minimum=1),
        ),
    )

    def __init__(self):
        self.enabled = False
        self.tasks = {}

    async def client_ready(self, client, db):
        self.client = client
        self._db = db

        self.enabled = self._db.get(self.name, "enabled", False)

        if self.enabled:
            self.restore_tasks()

    def restore_tasks(self):
        now = datetime.now(timezone.utc)

        for idx in (1, 2):
            if idx in self.tasks and not self.tasks[idx].done():
                continue

            if idx in self.tasks and not self.tasks[idx].done():
                self.tasks[idx].cancel()

            next_run = self._db.get(self.name, f"next_run_{idx}")
            delay = 0
            if next_run:
                delay = max(
                    0,
                    (datetime.fromisoformat(next_run) - now).total_seconds(),
                )

            self.tasks[idx] = asyncio.create_task(self.send_loop(idx, delay))

    async def send_ad(self, chat, text, photo):
        if photo != "None":
            await self.client.send_message(chat, text, file=photo)
        else:
            await self.client.send_message(chat, text)

    def add_log(self, idx, interval):
        key = f"logs_{idx}"
        logs = self._db.get(self.name, key, [])

        now = datetime.now(MSK).strftime("%d.%m.%Y %H:%M:%S")
        logs.insert(
            0,
            f"Афиша отправлена в {now} | КД {interval} мин"
        )

        self._db.set(self.name, key, logs[:20])

    async def send_loop(self, idx: int, delay: float = 0):
        await asyncio.sleep(delay)

        while self.enabled:
            try:
                chat = self.config[f"chat{idx}"]
                if chat != "None":
                    await self.send_ad(
                        chat,
                        self.config[f"text{idx}"],
                        self.config[f"photo{idx}"],
                    )
                    self.add_log(idx, self.config[f"interval{idx}"])

            except Exception:
                logger.exception(f"ClanAdvert error (chat {idx})")

            next_run = datetime.now(timezone.utc) + timedelta(
                minutes=self.config[f"interval{idx}"]
            )
            self._db.set(self.name, f"next_run_{idx}", next_run.isoformat())

            await asyncio.sleep(self.config[f"interval{idx}"] * 60)

    async def clan_cmd(self, message: Message):
        """
        Включить / выключить модуль
        """
        if not self.enabled:
            self.enabled = True
            self._db.set(self.name, "enabled", True)

            for idx in (1, 2):
                if idx in self.tasks and not self.tasks[idx].done():
                    self.tasks[idx].cancel()

                next_run = datetime.now(timezone.utc) + timedelta(
                    minutes=self.config[f"interval{idx}"]
                )
                self._db.set(self.name, f"next_run_{idx}", next_run.isoformat())
                self.tasks[idx] = asyncio.create_task(self.send_loop(idx))

            await utils.answer(
                message,
                self.strings["enabled"].format(
                    self.config["chat1"],
                    self.config["chat2"],
                ),
            )

        else:
            self.enabled = False
            self._db.set(self.name, "enabled", False)

            for task in self.tasks.values():
                task.cancel()
            self.tasks.clear()

            await utils.answer(message, self.strings["disabled"])

    async def logclan_cmd(self, message: Message):
        """
        Показать лог афиши 
        """
        msg = await utils.answer(message, "⏳ Загрузка лога...")

        logs1 = self._db.get(self.name, "logs_1", [])
        logs2 = self._db.get(self.name, "logs_2", [])

        if not logs1 and not logs2:
            await msg.edit(self.strings["log_empty"])
            return

        text = self.strings["log_title"]

        if logs1:
            text += "<b>1 чат:</b>\n"
            for i, log in enumerate(logs1, 1):
                text += f"{i}. {log}\n"
            text += "\n"

        if logs2:
            text += "<b>2 чат:</b>\n"
            for i, log in enumerate(logs2, 1):
                text += f"{i}. {log}\n"

        await msg.edit(text)

    async def uplogs_cmd(self, message: Message):
        """
        Очистить лог афиши
        """
        self._db.set(self.name, "logs_1", [])
        self._db.set(self.name, "logs_2", [])

        await utils.answer(message, self.strings["logs_cleared"])

    async def nullis_cmd(self, message: Message):
        """
        Сбросить все данные (включая логи и отправки)
        """
        self._db.set(self.name, "logs_1", [])
        self._db.set(self.name, "logs_2", [])
        self._db.set(self.name, "enabled", False)
        self._db.set(self.name, "next_run_1", None)
        self._db.set(self.name, "next_run_2", None)

        for task in self.tasks.values():
            task.cancel()
        self.tasks.clear()

        await utils.answer(message, self.strings["all_cleared"])