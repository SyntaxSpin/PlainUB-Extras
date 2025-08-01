from cowsay

from app import BOT, Message, bot


@bot.add_cmd(cmd="cowsay")
async def cowsay(bot: BOT, message: Message):
    text = message.input
    if not text:
        await message.reply("What is the cow supposed to say?")
        return

    cow_said = cow.Cowacter().milk(text)

    await message.reply(f"```\n{cow_said}\n```")
