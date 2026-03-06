from app import BOT, bot, Message

@bot.add_cmd(cmd="dm")
async def dm_command(bot: BOT, message: Message):
    args = message.text.split(" ", 2)
    
    target_user = None
    dm_text = ""

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user.id
        dm_text = message.text.split(" ", 1)[1] if len(args) > 1 else ""
    elif len(args) > 2:
        target_user = args[1]
        dm_text = args[2]
    
    if not target_user or not dm_text:
        await message.reply("write something to dm")
        return

    try:
        await bot.send_message(target_user, dm_text)
        await message.reply(f"Message sent to {target_user}")
    except Exception as e:
        await message.reply(f"Failed to send DM: {str(e)}")
