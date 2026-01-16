from .. import loader, utils
import asyncio

@loader.tds
class CaseOpenerMod2(loader.Module):
    """Модуль для автоматической отправки команды 'открыть кейс {case_id} {quantity}' в указанный чат"""

    strings = {
        "name": "CaseOpener2.0",
        "chat_id": "ID чата для отправки команды (none для отключения)",
        "case_id": "ID кейса для открытия (например, 2)",
        "quantity": "Количество кейсов для открытия (например, 250)",
        "state_on": "Автооткрытие кейсов включено!",
        "state_off": "Автооткрытие кейсов выключено!",
        "no_chat": "Укажите ID чата в конфиге!",
        "flood_wait": "<b>Защита от флуд-вейта (2 минуты отдыха)</b>"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "chat_id",
                "none",
                lambda: self.strings["chat_id"],
                validator=loader.validators.Union(
                    loader.validators.String(),
                    loader.validators.NoneType()
                )
            ),
            loader.ConfigValue(
                "case_id",
                "2",
                lambda: self.strings["case_id"],
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "quantity",
                "250",
                lambda: self.strings["quantity"],
                validator=loader.validators.String()
            )
        )
        self._active = False
        self._task = None
        self._message_count = 0

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self._active = self.db.get(self.strings["name"], "active", False)
        if self._active:
            self._task = asyncio.create_task(self._open_case_loop())

    async def _open_case_loop(self):
        """Цикл отправки команды 'открыть кейс {case_id} {quantity}'"""
        while self._active:
            chat_id = self.config["chat_id"]
            if chat_id == "none" or not chat_id:
                await asyncio.sleep(1)
                continue
            try:
                case_id = self.config["case_id"]
                quantity = self.config["quantity"]
                command = f"открыть кейс {case_id} {quantity}"
                await self.client.send_message(int(chat_id), command)
                self._message_count += 1
                if self._message_count >= 100:
                    await self.client.send_message(int(chat_id), self.strings["flood_wait"])
                    await asyncio.sleep(120)
                    self._message_count = 0
            except ValueError:
                await self.client.send_message("me", self.strings["no_chat"])
                self._active = False
                self.db.set(self.strings["name"], "active", False)
                break
            except Exception as e:
                await self.client.send_message("me", f"Ошибка: {str(e)}")
                self._active = False
                self.db.set(self.strings["name"], "active", False)
                break
            await asyncio.sleep(2)

    @loader.command()
    async def kase(self, message):
        """Включить или выключить автооткрытие кейсов"""
        if self._active:
            self._active = False
            if self._task:
                self._task.cancel()
            self.db.set(self.strings["name"], "active", False)
            await utils.answer(message, self.strings["state_off"])
        else:
            self._active = True
            self._message_count = 0
            self._task = asyncio.create_task(self._open_case_loop())
            self.db.set(self.strings["name"], "active", True)
            await utils.answer(message, self.strings["state_on"])
