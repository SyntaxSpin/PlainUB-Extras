import html
from pyrogram.types import Message, User, ReplyParameters

from app import BOT, bot

ERROR_VISIBLE_DURATION = 8

@bot.add_cmd(cmd="pfp")
async def pfp_handler(bot: BOT, message: Message):
    """
    CMD: PFP
    INFO: Fetches a user's current profile picture or video.
    USAGE:
        .pfp (on yourself)
        .pfp <user_id/username>
        .pfp (in reply to a user)
    """
    target_user: User = None

    if message.input:
        try:
            target_user = await bot.get_users(message.input)
        except Exception:
            return await message.edit("User not found.", del_in=ERROR_VISIBLE_DURATION)
    elif message.replied:
        target_user = message.replied.from_user
    else:
        target_user = message.from_user

    progress_message = await message.reply(f"<code>Fetching profile media for {target_user.first_name}...</code>")

    try:
        media_sent = False
        # We only need the first (most recent) item from the generator
        async for photo in bot.get_chat_photos(target_user.id, limit=1):
            
            # Check if it's a profile video
            if photo.video_file_id:
                await bot.send_video(
                    chat_id=message.chat.id,
                    video=photo.video_file_id,
                )
            # Otherwise, it's a static photo
            else:
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=photo.file_id,
                )
            
            media_sent = True
            break # Stop after the first item
        
        if not media_sent:
            return await progress_message.edit("This user has no profile picture or video.", del_in=ERROR_VISIBLE_DURATION)

        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not fetch profile media.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
