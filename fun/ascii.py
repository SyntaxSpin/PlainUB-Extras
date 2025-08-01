import pyfiglet

from app import BOT, Message, bot


@bot.add_cmd(cmd="ascii")
async def ascii(bot: BOT, message: Message):
    text = message.input
    if not text:
        await message.reply("What am I supposed to say?")
        return

    ascii_text = pyfiglet.figlet_format(text)

    await message.reply(f"```\n{ascii_text}\n```")
