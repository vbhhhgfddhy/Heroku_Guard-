__version__ = (4, 0, 2)

#  ======================================================================
# Название модуля: [AutoAction]
# Версия: [8.5.4]
# Описание: [Модуль для @Immortal_Cards_bot ]
# Автор: Heroku_Guard
# Канал и контакты: @heroku_guare, https://t.me/heroku_guard
# Дата создания: [02.03.2026]
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
# meta developer: @heroku_guard

import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta
from telethon.tl.types import Message
from telethon.errors import FloodWaitError
from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class SeparateAutoMod(loader.Module):
    """Стабильная авто-Арена и Подземелье"""

    strings = {
        "name": "AutoAction",

        "help": "🛠 <b>Команды:</b>\n"
                ".арена on/off\n"
                ".подземелье on/off\n"
                ".логи\n"
                ".задачи",

        "started_arena": "<emoji document_id=5123248930124989216>✅</emoji> Авто-арена запущена!",
        "started_dungeon": "<emoji document_id=5123248930124989216>✅</emoji> Авто-подземелье запущено!",
        "stopped_arena": "<emoji document_id=5100657930429006538>♥️</emoji> Авто-арена остановлена!",
        "stopped_dungeon": "<emoji document_id=5100657930429006538>♥️</emoji> Авто-подземелье остановлено!",
        "invalid_arg": "<emoji document_id=5116275208906343429>‼️</emoji> Используй on/off",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "arena_interval",
                40,
                lambda: "Интервал арены (мин)",
                validator=loader.validators.Integer(),
            ),
            loader.ConfigValue(
                "dungeon_interval",
                180,
                lambda: "Интервал подземелья (мин)",
                validator=loader.validators.Integer(),
            ),
        )

        self.bot_id = 6216165773

        
        self.arena_task = None
        self.dungeon_task = None

        
        self.arena_stop = asyncio.Event()
        self.dungeon_stop = asyncio.Event()

        
        self.next_arena_run = None
        self.next_dungeon_run = None

        
        self.arena_logs = []
        self.dungeon_logs = []

    async def client_ready(self, client, db):
        self._client = client
        self.db = db

        if self.db.get("SeparateAuto", "arena_status", False):
            await self._start_arena()

        if self.db.get("SeparateAuto", "dungeon_status", False):
            await self._start_dungeon()

    async def аренаcmd(self, message: Message):
        args = utils.get_args_raw(message).lower()

        if args == "on":
            await self._start_arena()
            self.db.set("SeparateAuto", "arena_status", True)
            await utils.answer(message, self.strings["started_arena"])

        elif args == "off":
            await self._stop_arena()
            self.db.set("SeparateAuto", "arena_status", False)
            await utils.answer(message, self.strings["stopped_arena"])

        else:
            await utils.answer(message, self.strings["invalid_arg"])

    async def подземельеcmd(self, message: Message):
        args = utils.get_args_raw(message).lower()

        if args == "on":
            await self._start_dungeon()
            self.db.set("SeparateAuto", "dungeon_status", True)
            await utils.answer(message, self.strings["started_dungeon"])

        elif args == "off":
            await self._stop_dungeon()
            self.db.set("SeparateAuto", "dungeon_status", False)
            await utils.answer(message, self.strings["stopped_dungeon"])

        else:
            await utils.answer(message, self.strings["invalid_arg"])

    async def логиcmd(self, message: Message):
        await utils.answer(
            message,
            "<b>📜 Последние 5 действий:</b>\n\n"
            "<b>Арена:</b>\n"
            + ("\n".join(self.arena_logs) if self.arena_logs else "Нет данных")
            + "\n\n<b>Подземелье:</b>\n"
            + ("\n".join(self.dungeon_logs) if self.dungeon_logs else "Нет данных")
        )

    async def задачиcmd(self, message: Message):

        def format_status(task, next_run):
            if not task or task.done():
                return "<emoji document_id=5121063440311386962>👎</emoji> Выключено"

            if next_run:
                delta = next_run - datetime.now()
                minutes = max(0, int(delta.total_seconds() // 60))
                return (
                    "<emoji document_id=5123163417326126159>✅</emoji> Включено\n"
                    f"<emoji document_id=5116163917713769254>⭐️</emoji> Запуск через {minutes} мин."
                )

            return "<emoji document_id=5123163417326126159>✅</emoji> Работает..."

        await utils.answer(
            message,
            "<emoji document_id=5116116063188157350>🥷</emoji> <b>Статус модулей:</b>\n\n"
            f"<b>Арена:</b> {format_status(self.arena_task, self.next_arena_run)}\n\n"
            f"<b>Подземелье:</b> {format_status(self.dungeon_task, self.next_dungeon_run)}"
        )

    async def _start_arena(self):
        if self.arena_task and not self.arena_task.done():
            return

        self.arena_stop.clear()
        self.arena_task = asyncio.create_task(self._arena_loop())

    async def _stop_arena(self):
        self.arena_stop.set()

        if self.arena_task:
            self.arena_task.cancel()
            try:
                await self.arena_task
            except:
                pass

        self.next_arena_run = None

    async def _start_dungeon(self):
        if self.dungeon_task and not self.dungeon_task.done():
            return

        self.dungeon_stop.clear()
        self.dungeon_task = asyncio.create_task(self._dungeon_loop())

    async def _stop_dungeon(self):
        self.dungeon_stop.set()

        if self.dungeon_task:
            self.dungeon_task.cancel()
            try:
                await self.dungeon_task
            except:
                pass

        self.next_dungeon_run = None

    async def _arena_loop(self):
        try:
            while not self.arena_stop.is_set():

                await self._safe_send("арена")
                await asyncio.sleep(2)

                messages = await self._client.get_messages(self.bot_id, limit=1)
                if not messages:
                    continue

                bot_msg = messages[0]
                attempts = self._parse_attempts(bot_msg.raw_text)

                for _ in range(attempts):
                    if self.arena_stop.is_set():
                        return

                    await self._click_button(bot_msg, 1)
                    await asyncio.sleep(2)
                    await self._click_button(bot_msg, 2)
                    await asyncio.sleep(2)
                    await self._click_button(bot_msg, 2)
                    await asyncio.sleep(2)

                    bot_msg = await self._client.get_messages(
                        self.bot_id, ids=bot_msg.id
                    )

                self._add_log("arena", f"Успешно ({attempts} боев)")

                interval = self.config["arena_interval"] * 60
                self.next_arena_run = datetime.now() + timedelta(seconds=interval)

                try:
                    await asyncio.wait_for(
                        self.arena_stop.wait(),
                        timeout=interval
                    )
                except asyncio.TimeoutError:
                    pass

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception("Arena crash:", exc_info=e)
            self._add_log("arena", f"Ошибка: {str(e)[:20]}")
        finally:
            self.next_arena_run = None

    async def _dungeon_loop(self):
        try:
            while not self.dungeon_stop.is_set():

                await self._safe_send("арена ")
                await asyncio.sleep(2)

                messages = await self._client.get_messages(self.bot_id, limit=1)
                if not messages:
                    continue

                bot_msg = messages[0]

                sequence = [6, 1, 1, 2, 2, 6, 2, 1, 2, 2]

                for btn_index in sequence:
                    if self.dungeon_stop.is_set():
                        return

                    bot_msg = await self._client.get_messages(
                        self.bot_id, ids=bot_msg.id
                    )

                    if not bot_msg.reply_markup:
                        break

                    buttons = [
                        btn
                        for row in bot_msg.reply_markup.rows
                        for btn in row.buttons
                        if hasattr(btn, "data") and btn.data
                    ]

                    if btn_index > len(buttons):
                        break

                    await bot_msg.click(data=buttons[btn_index - 1].data)
                    await asyncio.sleep(2.5)

                self._add_log("dungeon", "Успешно")

                interval = self.config["dungeon_interval"] * 60
                self.next_dungeon_run = datetime.now() + timedelta(seconds=interval)

                try:
                    await asyncio.wait_for(
                        self.dungeon_stop.wait(),
                        timeout=interval
                    )
                except asyncio.TimeoutError:
                    pass

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception("Dungeon crash:", exc_info=e)
            self._add_log("dungeon", f"Ошибка: {str(e)[:20]}")
        finally:
            self.next_dungeon_run = None

    async def _safe_send(self, text):
        try:
            await self._client.send_message(self.bot_id, text)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
        except Exception as e:
            logger.error(f"Send error: {e}")

    def _parse_attempts(self, text):
        if "Попыток:" not in text:
            return 0
        try:
            return int(text.split("Попыток:")[1].strip().split("\n")[0])
        except:
            return 0

    def _add_log(self, mode, text):
        now = datetime.now().strftime("%H:%M:%S")
        log = f"[{now}] {text}"

        if mode == "arena":
            self.arena_logs.append(log)
            if len(self.arena_logs) > 5:
                self.arena_logs.pop(0)
        else:
            self.dungeon_logs.append(log)
            if len(self.dungeon_logs) > 5:
                self.dungeon_logs.pop(0)

    async def _click_button(self, msg, btn_num):
        msg = await self._client.get_messages(self.bot_id, ids=msg.id)
        if not msg.reply_markup:
            return

        buttons = [
            btn
            for row in msg.reply_markup.rows
            for btn in row.buttons
            if hasattr(btn, "data") and btn.data
        ]

        if len(buttons) >= btn_num:
            try:
                await msg.click(data=buttons[btn_num - 1].data)
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 1)
