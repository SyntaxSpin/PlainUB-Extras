import html
from pyrogram.types import Message, User, ReplyParameters

from app import BOT, bot

ERROR_VISIBLE_DURATION = 8

@bot.add_cmd(cmd="pfp")
async def pfp_handler(bot: BOT, message: Message):
    """
    CMD: PFP
    INFO: Fetches a user's current profile picture (or video thumbnail).
    USAGE:
        .pfp (on yourself)
        .pfp [user_id/username]
        .pfp (in reply to a user)
    """
    target_user: User = None

    if message.input:
        try:
            target_user = await bot.get_users(message.input)
        except Exception:
            return await message.reply("User not found.", del_in=ERROR_VISIBLE_DURATION)
    elif message.replied:
        target_user = message.replied.from_user
    else:
        target_user = message.from_user

    progress_message = await message.reply(f"<code>Fetching {target_user.first_name} profile photo...</code>")

    try:
        media_sent = False
        async for photo in bot.get_chat_photos(target_user.id, limit=1):
            
            caption_text = f"{target_user.mention} profile photo."
            
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=photo.file_id,
                caption=caption_text,
                reply_parameters=ReplyParameters(message_id=message.id)
            )
            
            media_sent = True
            break
        
        if not media_sent:
            return await message.reply("This user has no profile photo.", del_in=ERROR_VISIBLE_DURATION)

        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not fetch profile photo.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
