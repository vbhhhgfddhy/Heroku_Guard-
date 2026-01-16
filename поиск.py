# meta developer: @ModuliBFG_canal 

# ======================================================================
# Название модуля: [поиск]
# Версия: [2.0.0]
# Описание: [ищит модули в канале.]
# Автор: Heroku_Guard
# Канал и контакты: @ModuliBFG_canal, https://t.me/ModuliBFG_canal
# Дата создания: [16.01.2026]
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
from .. import loader, utils
from herokutl.tl.custom import Button         

@loader.tds
class BFGModuleSearch(loader.Module):
    """Поиск модулей по названию, описанию и командам строго в одном канале"""
    strings = {"name": "поиск"}

    def __init__(self):
        # Канал для поиска
        self.channel = "ModuliBFG_canal"
        self.last_results = {}

    @loader.command(ru_doc="Ищет модуль по названию, описанию или команде")
    async def heta(self, message):
        query = utils.get_args_raw(message)
        if not query:
            await message.edit("❌ Укажите текст для поиска.")
            return

        user_id = message.sender_id
        self.last_results.pop(user_id, None) 
        results = []

        try:
            async for msg in self._client.iter_messages(self.channel, limit=1000):
                module_info = self._parse_module(msg)
                if module_info and self._match_query(query, module_info):
                    results.append(module_info)
        except Exception:
            await message.edit("❌ Ошибка при получении сообщений из канала.")
            return

        if not results:
            await message.edit("❌ Модуль не найден")
            return

        self.last_results[user_id] = {
            "results": results,
            "index": 0,
            "chat_id": message.chat_id
        }

        await self._send_result(user_id)

    async def _send_result(self, user_id):
        """Отправка текущего результата с кнопкой и аккуратным форматированием"""
        data = self.last_results[user_id]
        module = data["results"][data["index"]]

        commands_lines = module.get("commands", "").splitlines()
        commands = []
        for idx, line in enumerate(commands_lines, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            cmd = parts[0]
            desc = parts[1] if len(parts) > 1 else ""
            if desc:
                commands.append(f"{idx}. <code>{cmd}</code> — {desc}")
            else:
                commands.append(f"{idx}. <code>{cmd}</code>")
        commands_text = "\n".join(commands)

        install_text = f"<code>{module.get('install', '')}</code>"

        ps_text = module.get("ps", "").strip()
        if ps_text:
            ps_text = f"\n\nP.S — {ps_text}"

        text = (
            f"<emoji document_id=5134452506935427991>🪐</emoji>  Название: {module.get('name')}\n\n"
            f"<emoji document_id=5879813604068298387>ℹ️</emoji> Описание: {module.get('description')}\n\n"
            f"<emoji document_id=5370932688993656500>🌕</emoji>  Команды:\n{commands_text}{ps_text}\n\n"
            f"<emoji document_id=4916086774649848789>🔗</emoji> Установка:\n{install_text}"
        )

        buttons = [[Button.inline("🔄 Поменять результат", f"heta_next:{user_id}")]]

        if "msg_id" in data:
            try:
                await self._client.edit_message(
                    data["chat_id"], data["msg_id"], text, buttons=buttons, parse_mode="html"
                )
            except Exception:
                sent = await self._client.send_message(data["chat_id"], text, buttons=buttons, parse_mode="html")
                data["msg_id"] = sent.id
        else:
            sent = await self._client.send_message(data["chat_id"], text, buttons=buttons, parse_mode="html")
            data["msg_id"] = sent.id

    async def watcher(self, update):
        """Обработка нажатия кнопки"""
        if hasattr(update, "data") and update.data.startswith("heta_next:"):
            user_id = int(update.data.split(":")[1])
            if user_id in self.last_results:
                data = self.last_results[user_id]
                data["index"] = (data["index"] + 1) % len(data["results"])
                await self._send_result(user_id)
            await update.answer()

    def _parse_module(self, msg):
        """Парсинг сообщения модуля"""
        text = msg.message or getattr(msg.media, "caption", None)
        if not text:
            return None

        name_match = re.search(r"Название[:\-]?\s*(.+)", text, re.IGNORECASE)
        desc_match = re.search(r"Описание[:\-]?\s*(.+)", text, re.IGNORECASE)
        commands_match = re.search(r"Команды[:\-]?\s*([\s\S]*?)(?:\nУстановка|$)", text, re.IGNORECASE)
        install_match = re.search(r"Установка[:\-]?\s*(.+)", text, re.IGNORECASE)
        ps_match = re.search(r"P\.S\s*[:\-]?\s*(.+)", text, re.IGNORECASE)

        if not name_match:
            return None

        return {
            "name": name_match.group(1).strip(),
            "description": desc_match.group(1).strip() if desc_match else "Нет описания",
            "commands": commands_match.group(1).strip() if commands_match else "",
            "install": install_match.group(1).strip() if install_match else "",
            "ps": ps_match.group(1).strip() if ps_match else ""
        }

    def _match_query(self, query, module_info):
        q = query.lower()
        return any(q in (module_info.get(k, "").lower().replace("\n", " ")) for k in ["name", "description", "commands"])
