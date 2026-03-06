from app import BOT, bot, Message
from pyrogram.enums import ChatType

@bot.add_cmd(cmd="dm")
async def dm_handler(bot: BOT, message: Message):
    target_user = None
    
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user.id
    elif len(message.text.split()) > 1:
        user_input = message.text.split(None, 1)[1]
        try:
            user_obj = await bot.get_users(user_input)
            target_user = user_obj.id
        except Exception:
            return await message.reply("User not found.")
    else:
        return await message.reply("Reply to someone or provide a username/ID.")

    try:
        await bot.send_message(target_user, "Hello! I am messaging you via the DM command.")
        await message.reply(f"Successfully sent a message to `{target_user}`.")
    except Exception as e:
        await message.reply(f"Failed to DM: {e}")
