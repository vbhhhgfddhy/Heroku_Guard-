from .. import loader, utils
import asyncio
import json

@loader.tds
class ПересылкаMod(loader.Module):
    """Пампампам"""
    strings = {"name": "Пересылка"}

    def __init__(self):
        self.job_counter = 0
        self.jobs = {}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

        saved_jobs_json = self.db.get("Пересылка", "jobs", "[]")
        try:
            saved_jobs = json.loads(saved_jobs_json)
        except Exception:
            saved_jobs = []

        for job in saved_jobs:
            self.job_counter += 1
            job_id = self.job_counter
            message_id = job.get("message_id")
            to_id = job.get("to_id")
            interval = job.get("interval")
            if message_id and to_id and interval:
                await self.start_forward(job_id, message_id, to_id, interval)

    def get_peer_id(self, peer):
        if hasattr(peer, "user_id"):
            return peer.user_id
        elif hasattr(peer, "chat_id"):
            return peer.chat_id
        elif hasattr(peer, "channel_id"):
            return peer.channel_id
        else:
            try:
                return int(peer)
            except Exception:
                return None

    async def start_forward(self, job_id, message_id, to_id, interval):
        async def forward_loop():
            try:
                while True:
                    await asyncio.sleep(interval)
                    try:
                        await self.client.forward_messages(to_id, message_id, to_id)
                    except Exception:
                        break
            except asyncio.CancelledError:
                pass

        task = asyncio.create_task(forward_loop())
        self.jobs[job_id] = task

    async def aforwardcmd(self, message):
        """Запускает пересылку с указанным интервалом"""
        args = utils.get_args(message)
        if not args or not message.is_reply:
            await message.edit("Использование: .aforward <время> (например, 50s, 10m, 2h) ответом на сообщение")
            return

        time_str = args[0]
        if time_str[-1] not in "smh":
            await message.edit("Неверный формат времени. Используй s, m или h в конце")
            return

        try:
            interval_value = int(time_str[:-1])
        except Exception:
            await message.edit("Неверное значение времени")
            return

        multiplier = {"s":1, "m":60, "h":3600}[time_str[-1]]
        interval = interval_value * multiplier

        reply_message = await message.get_reply_message()
        self.job_counter += 1
        job_id = self.job_counter

        to_id = self.get_peer_id(message.to_id)
        if to_id is None:
            await message.edit("Не удалось определить ID получателя")
            return

        await self.start_forward(job_id, reply_message.id, to_id, interval)
        await message.edit(f"Пересылка #{job_id} запущена каждые {interval} секунд.")

        jobs_json = self.db.get("Пересылка", "jobs", "[]")
        try:
            jobs = json.loads(jobs_json)
        except Exception:
            jobs = []

        jobs.append({"message_id": reply_message.id, "to_id": to_id, "interval": interval})
        self.db.set("Пересылка", "jobs", json.dumps(jobs))

    async def stopforwardcmd(self, message):
        """Останавливает пересылку"""
        args = utils.get_args(message)
        if not args:
            await message.edit("Использование: .stopforward <номер> или .stopforward all")
            return

        jobs_json = self.db.get("Пересылка", "jobs", "[]")
        try:
            jobs = json.loads(jobs_json)
        except Exception:
            jobs = []

        if args[0].lower() == "all":
            for task in self.jobs.values():
                task.cancel()
            self.jobs.clear()
            self.job_counter = 0
            self.db.set("Пересылка", "jobs", json.dumps([]))
            await message.edit("Остановлены все пересылки")
            return

        try:
            job_id = int(args[0])
        except Exception:
            await message.edit("Тут число должно быть")
            return

        if job_id in self.jobs:
            self.jobs[job_id].cancel()
            del self.jobs[job_id]
            if 0 <= job_id-1 < len(jobs):
                jobs.pop(job_id-1)
            self.db.set("Пересылка", "jobs", json.dumps(jobs))
            await message.edit(f"Пересылка #{job_id} остановлена")
        else:
            await message.edit("Такой пересылки нет")