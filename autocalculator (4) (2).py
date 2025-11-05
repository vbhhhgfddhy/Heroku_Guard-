from .. import loader, utils
from telethon import events
from telethon.tl.types import Message
import math
import re
import json
import os

# meta developer: https://t.me/heroku_model

@loader.tds
class AutoCalculator(loader.Module):
    """Автоматический калькулятор с настраиваемым выводом"""

    strings = {
        "name": "AutoCalculator",
        "invalid_expression": "Неверное математическое выражение.",
        "enabled_in_chat": "Калькулятор включён в этом чате.",
        "disabled_in_chat": "Калькулятор выключен в этом чате.",
        "all_disabled": "Калькулятор был выключен во всех чатах.",
    }

    def __init__(self):
        self._enabled_chats = {}
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "response_text",
                "<blockquote><emoji document_id=5345808139629370973>🤷‍♀️</emoji> хочешь узнать ответ?</blockquote>"
                "<blockquote> а вот твой и ответ: {result}<emoji document_id=5359665306149068850>😍</emoji></blockquote>",
                doc="Текстовый шаблон для вывода результата. Используйте {result} для результата вычисления."
            ),
        )
        self._handler_added = False

    async def client_ready(self, client, db):
        self._client = client
        self._me = await client.get_me()

        file_path = "enabled_chats.json"
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self._enabled_chats = json.load(f)
            except Exception as e:
                print(f"Ошибка при загрузке состояния: {e}")
        else:
            self._enabled_chats = {}

        if not self._handler_added:
            self._client.add_event_handler(self._on_message, events.NewMessage())
            self._handler_added = True

    @loader.command()
    async def startkulkulator(self, message: Message):
        """Включить калькулятор в этом чате"""
        chat_id = str(message.chat_id)
        if chat_id not in self._enabled_chats or not self._enabled_chats[chat_id]:
            self._enabled_chats[chat_id] = True
            await message.reply(self.strings["enabled_in_chat"])
            self._save_state()
        else:
            await message.reply("Калькулятор уже включён в этом чате.")

    @loader.command()
    async def stopkulkulator(self, message: Message):
        """Выключить калькулятор в этом чате"""
        chat_id = str(message.chat_id)
        if chat_id in self._enabled_chats and self._enabled_chats[chat_id]:
            self._enabled_chats[chat_id] = False
            await message.reply(self.strings["disabled_in_chat"])
            self._save_state()
        else:
            await message.reply("Калькулятор не включён в этом чате.")

    @loader.command()
    async def stopallkulkulator(self, message: Message):
        """Выключить калькулятор во всех чатах"""
        if self._enabled_chats:
            self._enabled_chats = {chat_id: False for chat_id in self._enabled_chats}
            await message.reply(self.strings["all_disabled"])
            for chat_id in self._enabled_chats:
                try:
                    await self._client.send_message(chat_id, self.strings["disabled_in_chat"])
                except Exception as e:
                    print(f"Ошибка при отправке сообщения в чат {chat_id}: {e}")
            self._save_state()
        else:
            await message.reply("Калькулятор не был включён в каких-либо чатах.")

    async def _on_message(self, event):
        message = event.message
        text = message.text.strip()

        if message.sender_id == self._me.id:
            return

        chat_id = str(message.chat_id)
        if not self._enabled_chats.get(chat_id, False):
            return

        if self._is_simple_number(text):
            return

        if self._is_math_expression(text):
            try:
                # Заменяем ^ на ** для возведения в степень
                expression = text.replace("^", "**")
                result = await self._calculate_expression(expression)

                response_text = self.config["response_text"].format(result=result)
                await message.reply(response_text)

            except ZeroDivisionError:
                await message.reply("Ошибка: деление на ноль!")
            except Exception:
                await message.reply(self.strings["invalid_expression"])

    async def _calculate_expression(self, expression: str):
        """Асинхронный метод для безопасного вычисления математического выражения"""
        try:
            result = eval(expression, {"__builtins__": None}, {"math": math, "e": math.e})
            return result
        except Exception as e:
            raise ValueError(f"Ошибка при вычислении выражения: {e}")

    def _is_math_expression(self, text: str) -> bool:
        """
        Проверяет, является ли текст математическим выражением.
        Только выражения с хотя бы одним числом будут обработаны.
        """
        text = text.strip()
        pattern = r'^[0-9+\-*/%^().e ]+$'
        if not re.match(pattern, text):
            return False
        # Есть ли хотя бы одна цифра
        return bool(re.search(r'\d', text))

    def _is_simple_number(self, text: str) -> bool:
        """
        Проверяет, является ли сообщение просто числом или списком чисел
        (например: "4", "3 5 7 9" или "3.14 2.7")
        """
        return bool(re.match(r'^-?\d+(\.\d+)?(\s-?\d+(\.\d+)?)*$', text.strip()))

    def _save_state(self):
        """Сохраняет состояние калькулятора в JSON файл"""
        file_path = "enabled_chats.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self._enabled_chats, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка при сохранении состояния: {e}")
