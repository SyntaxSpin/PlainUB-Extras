from app import BOT, bot, Message

@bot.add_cmd(cmd="dm")
async def dm_command(bot: BOT, message: Message):
    args = message.text.split(" ", 2)
    user = None
    text = ""

    if message.reply_to_message:
        user = message.reply_to_message.from_user.id
        text = message.text.split(" ", 1)[1] if len(args) > 1 else ""
    elif len(args) > 2:
        user = args[1]
        text = args[2]

    if not user or not text:
        await message.reply("write something to dm")
        return

    try:
        await bot.send_message(user, text)
    except Exception as e:
        await message.reply(f"Error: {str(e)}")
