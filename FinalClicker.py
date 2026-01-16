import logging
import asyncio
from telethon.tl.types import Message
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class AutoClickerByIndexMod(loader.Module):
    """Автокликер с исправленными валидаторами"""
    
    strings = {
        "name": "FinalClicker",
        "help": "🛠 <b>Команды:</b>\n"
                ".clicks <1-1000>\n.delay <1-1500>\n.btn <номер>\n.autoclick\n.stop",
        "set_clicks": "⚡ Клики: {}",
        "set_delay": "⚡ Интервал: {} сек.",
        "set_button": "⚡ Кнопка №{}",
        "started": "✅ Старт: {} кликов, кнопка №{}, интервал {} сек!",
        "error_reply": "🚫 Ответь на сообщение с кнопками!",
        "error_button": "🚫 Неверная кнопка! Всего: {}",
        "error_no_buttons": "🚫 Нет кнопок!",
        "done": "✅ Готово! Успешно: {}",
        "invalid": "🚫 Неверное значение!",
        "stopped": "⛔ Остановлено! Успешно: {}",
        "not_running": "🚫 Не запущено!"
    }

    def __init__(self):
        # Убраны валидаторы, проверка будет внутри команд
        self.config = loader.ModuleConfig(
            loader.ConfigValue("clicks", 100, "Количество кликов"),
            loader.ConfigValue("delay", 5, "Интервал"),
            loader.ConfigValue("button_num", 1, "Номер кнопки")
        )
        self.is_running = False
        self.success = 0

    async def autoclickcmd(self, message: Message):
        """Запуск кликера"""
        if self.is_running:
            return await utils.answer(message, "🚫 Уже работает!")
        
        reply = await message.get_reply_message()
        if not reply or not getattr(reply, 'reply_markup', None):
            return await utils.answer(message, self.strings["error_reply"])

        try:
            # Безопасная проверка: data может быть int, bytes или str
            buttons = [
                btn
                for row in getattr(reply.reply_markup, 'rows', [])
                for btn in getattr(row, 'buttons', [])
                if hasattr(btn, "data") and btn.data is not None
            ]
            if not buttons:
                return await utils.answer(message, self.strings["error_no_buttons"])
            
            if self.config["button_num"] > len(buttons):
                return await utils.answer(
                    message,
                    self.strings["error_button"].format(len(buttons))
                )
            
            button = buttons[self.config["button_num"] - 1]
        except Exception as e:
            logger.error(f"Error: {e}")
            return await utils.answer(message, self.strings["error_no_buttons"])

        self.is_running = True
        self.success = 0

        await utils.answer(
            message,
            self.strings["started"].format(
                self.config["clicks"],
                self.config["button_num"],
                self.config["delay"]
            )
        )

        try:
            for _ in range(self.config["clicks"]):
                if not self.is_running:
                    break
                
                await reply.click(data=button.data)
                self.success += 1
                await asyncio.sleep(self.config["delay"])
            
            await utils.answer(message, self.strings["done"].format(self.success))
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await utils.answer(message, f"🚫 Ошибка: {str(e)}")
        finally:
            self.is_running = False

    async def stoppcmd(self, message: Message):
        """Остановка"""
        if not self.is_running:
            return await utils.answer(message, self.strings["not_running"])
        
        self.is_running = False
        await utils.answer(message, self.strings["stopped"].format(self.success))

    async def clickscmd(self, message: Message):
        """Установка кликов"""
        args = utils.get_args_raw(message)
        if not args.isdigit():
            return await utils.answer(message, self.strings["invalid"])
        
        value = int(args)
        if 1 <= value <= 1000:
            self.config["clicks"] = value
            await utils.answer(message, self.strings["set_clicks"].format(value))
        else:
            await utils.answer(message, self.strings["invalid"])

    async def delaycmd(self, message: Message):
        """Установка интервала"""
        args = utils.get_args_raw(message)
        if not args.isdigit():
            return await utils.answer(message, self.strings["invalid"])
        
        value = int(args)
        if 1 <= value <= 1500:
            self.config["delay"] = value
            await utils.answer(message, self.strings["set_delay"].format(value))
        else:
            await utils.answer(message, self.strings["invalid"])

    async def btncmd(self, message: Message):
        """Выбор кнопки"""
        args = utils.get_args_raw(message)
        if not args.isdigit():
            return await utils.answer(message, self.strings["invalid"])
        
        value = int(args)
        if value >= 1:
            self.config["button_num"] = value
            await utils.answer(message, self.strings["set_button"].format(value))
        else:
            await utils.answer(message, self.strings["invalid"])

    async def client_ready(self, client, db):
        self._client = client
