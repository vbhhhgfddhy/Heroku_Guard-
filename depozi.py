import asyncio
import datetime
from .. import loader, utils

@loader.tds
class DepositModule(loader.Module):
    """Модуль отправки сообщений через каждые 4 дня."""

    strings = {"name": "DepositMessages"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "command",
                "startdep",
                "Команда для управления модулем."
            )
        )

    async def client_ready(self, _, db):
        self.db = db
        self.loop = asyncio.get_event_loop()

        if self.db.get("DepositModule", "enabled") is None:
            self.db.set("DepositModule", "enabled", False)

        if self.db.get("DepositModule", "last_run") is None:
            self.db.set("DepositModule", "last_run", str(datetime.datetime.utcnow()))

        self.loop.create_task(self.schedule_deposit_messages())

    async def schedule_deposit_messages(self):
        while True:
            enabled = self.db.get("DepositModule", "enabled", False)
            if enabled:
                last_run_str = self.db.get("DepositModule", "last_run", str(datetime.datetime.utcnow()))
                last_run = datetime.datetime.fromisoformat(last_run_str)

                now_utc = datetime.datetime.utcnow()
                if now_utc - last_run >= datetime.timedelta(days=4):
                    await self.send_deposit_messages()
                    self.db.set("DepositModule", "last_run", now_utc.isoformat())

            await asyncio.sleep(600)

    async def send_deposit_messages(self):
        bot = await self.client.get_me()

        await self.client.send_message(bot.id, "депозит снять все")
        await asyncio.sleep(180)

        await self.client.send_message(bot.id, "депозит положить всё")

    @loader.command(name="startdep")
    async def startdepcmd(self, message):
        enabled = self.db.get("DepositModule", "enabled", False)

        if enabled:
            self.db.set("DepositModule", "enabled", False)
            await message.reply("<b>Модуль выключен.</b>")
        else:
            self.db.set("DepositModule", "enabled", True)
            await message.reply("<b>Модуль включен.</b>")

