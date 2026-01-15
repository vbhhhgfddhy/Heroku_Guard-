import asyncio
from telethon.errors.rpcerrorlist import YouBlockedUserError, FloodWaitError
from telethon.tl.functions.contacts import UnblockRequest
from telethon.tl.functions.messages import ReadMentionsRequest
from telethon.tl.types import Message

from .. import loader, utils


@loader.tds
class AutoBFGmod(loader.Module):
    """Автоматически поливает сад и оплачивает налоги бизнесов в BFG"""
    
    strings = {"name": "AutoBFG"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "time",
                60,
                lambda: "Пауза между циклами (в минутах)",
                validator=loader.validators.Integer(minimum=1),
            ),
            loader.ConfigValue(
                "auto_chat",
                "@bfgproject",
                lambda: "Чат для автосада",
                validator=loader.validators.String(),
            ),
        )

    async def client_ready(self, client, db):
        self._client = client
        self._db = db

        # Запуск цикла при включенной настройке
        if self.get("garden", False):
            asyncio.create_task(self.auto_garden_loop())

        try:
            await client.send_message(
                self.config["auto_chat"],
                "<emoji document_id=5219943216781995020>⚡</emoji> <b>Модуль AutoBFG установлен</b>",
            )
        except YouBlockedUserError:
            await client(UnblockRequest(self.config["auto_chat"]))
            await client.send_message(
                self.config["auto_chat"],
                "<emoji document_id=5219943216781995020>⚡</emoji> <b>Модуль AutoBFG установлен</b>",
            )
        except Exception as e:
            await client.send_message(
                "me",
                f"<emoji document_id=5427057273168841103>🚫</emoji> <b>Ошибка инициализации AutoBFG: {str(e)}</b>",
            )

    async def _autogarden(self):
        try:
            chat = self.config["auto_chat"]
            async with self._client.conversation(chat, timeout=10) as conv:
                await conv.send_message("Мой сад")
                resp = await conv.get_response()
                await asyncio.sleep(1)
                await resp.click(text="💦 Полить сад")
                await asyncio.sleep(2)
                await resp.click(text="💸 Оплатить налоги")
                await asyncio.sleep(3)

                # Поливаем дерево
                await conv.send_message("Моё дерево")
                resp = await conv.get_response()
                await asyncio.sleep(1)
                await resp.click(text="💸 Оплатить налоги")
                await asyncio.sleep(3)

                # Оплата генератора
                await conv.send_message("Мой генератор")
                resp = await conv.get_response()
                await asyncio.sleep(1)
                await resp.click(text="💸 Оплатить налоги")
                await asyncio.sleep(3)

                # Оплата карьера 
                await conv.send_message("Мой карьер")
                resp = await conv.get_response()
                await asyncio.sleep(1)
                await resp.click(text="💸 Оплатить налоги")
                await asyncio.sleep(3)

                # Оплата бизнеса
                await conv.send_message("Мой бизнес")
                resp = await conv.get_response()
                await asyncio.sleep(1)
                await resp.click(text="💸 Оплатить налоги")
                await asyncio.sleep(3)

                # Ферма
                await conv.send_message("Моя ферма")
                resp = await conv.get_response()
                await asyncio.sleep(1)
                await resp.click(text="💸 Оплатить налоги") 

            return True

        except (TimeoutError, FloodWaitError) as e:
            await self._client.send_message("me", f"<emoji document_id=5427057273168841103>🚫</emoji> <b>Ошибка работы с садом: {str(e)}</b>")
            return False
        except Exception as e:
            await self._client.send_message("me", f"<emoji document_id=5427057273168841103>🚫</emoji> <b>Ошибка: {str(e)}</b>")
            return False

    async def auto_garden_loop(self):
        while self.get("garden", False):
            success = await self._autogarden()
            if success:
                try:
                    # Читаем упоминания для возможных дополнительных действий
                    await self._client(ReadMentionsRequest(self.config["auto_chat"]))
                    # Можно добавить дополнительные действия здесь
                except Exception:
                    pass
            # Задержка между итерациями (в минутах)
            delay_seconds = 60 * self.config["time"]
            await asyncio.sleep(delay_seconds)

    @loader.command(ru_doc="Запуск/остановка автополива и уплаты налогов")
    async def autogardencmd(self, message: Message):
        prefix = self.get_prefix()
        if self.get("garden", False):
            # Остановка автоматизации
            self.set("garden", False)
            await utils.answer(message, "<emoji document_id=5407091670766343316>📛</emoji> <b>AutoGarden остановлен</b>")
        else:
            # Запуск автоматизации
            self.set("garden", True)
            asyncio.create_task(self.auto_garden_loop())
            await utils.answer(
                message,
                f"<emoji document_id=5355127832114645894>🌳</emoji> <b>AutoGarden запущен\nДля остановки используйте <code>{prefix}autogarden</code></b>"
            )