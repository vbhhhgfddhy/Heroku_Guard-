# ---------------------------------------------------------------------------------
#  /\_/\  🌐 Этот модуль загружен через https://t.me/hikkamods_bot
# ( o.o )  🔓 Не лицензирован.
#  > ^ <   ⚠️ Владелец heta.hikariatama.ru не берет на себя ответственность или права интеллектуальной собственности за этот скрипт
# ---------------------------------------------------------------------------------
# Название: spam
# Описание: Модуль спама
# Автор: Fl1yd
# Команды:
# .spam | .cspam | .wspam | .delayspam
# ---------------------------------------------------------------------------------


from asyncio import gather, sleep

from .. import loader, utils


def register(cb):
    cb(SpamMod())


class SpamMod(loader.Module):
    """Спам модуль"""

    strings = {"name": "Spam"}

    async def spamcmd(self, message):
        """Обычный спам. Используй .spam <кол-во:int> <текст или реплай>."""
        try:
            await message.delete()
            args = utils.get_args(message)
            count = int(args[0].strip())
            reply = await message.get_reply_message()
            if reply:
                if reply.media:
                    for _ in range(count):
                        await message.client.send_file(message.to_id, reply.media)
                else:
                    for _ in range(count):
                        await message.client.send_message(message.to_id, reply)
            else:
                text = " ".join(args[1:])
                for _ in range(count):
                    await message.respond(text)
        except:
            return await message.client.send_message(
                message.to_id, ".spam <кол-во:int> <текст или реплай>."
            )

    async def cspamcmd(self, message):
        """Спам символами. Используй .cspam <текст или реплай>."""
        await message.delete()
        reply = await message.get_reply_message()
        if reply:
            msg = reply.text
        else:
            msg = utils.get_args_raw(message)
        msg = msg.replace(" ", "")
        for m in msg:
            await message.respond(m)

    async def wspamcmd(self, message):
        """Спам словами. Используй .wspam <текст или реплай>."""
        await message.delete()
        reply = await message.get_reply_message()
        if reply:
            msg = reply.text
        else:
            msg = utils.get_args_raw(message)
        msg = msg.split()
        for m in msg:
            await message.respond(m)

    async def delayspamcmd(self, message):
        """Спам с задержкой. Используй .delayspam <время:int> <кол-во:int> <текст или реплай>."""
        try:
            await message.delete()
            args = utils.get_args_raw(message)
            reply = await message.get_reply_message()
            parts = args.split(" ", 2)
            time = int(parts[0])
            count = int(parts[1])
            spam_text = parts[2] if len(parts) > 2 else ""

            if reply:
                if reply.media:
                    for _ in range(count):
                        await message.client.send_file(
                            message.to_id, reply.media, reply_to=reply.id
                        )
                        await sleep(time)
                else:
                    for _ in range(count):
                        await message.client.send_message(
                            message.to_id, spam_text, reply_to=reply.id
                        )
                        await sleep(time)
            else:
                for _ in range(count):
                    await message.client.send_message(
                        message.to_id, spam_text
                    )
                    await sleep(time)
        except:
            return await message.client.send_message(
                message.to_id, ".delayspam <время:int> <кол-во:int> <текст или реплай>"
            )