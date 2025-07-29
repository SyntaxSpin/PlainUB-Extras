import os
import html
from pyrogram.types import Message, User, ReplyParameters

from app import BOT, bot

TEMP_DIR = "temp_pfp/"
os.makedirs(TEMP_DIR, exist_ok=True)
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
    
    file_path = None
    try:
        # Download the highest quality profile media. Pyrogram handles getting the video if it exists.
        file_path = await bot.download_media(
            message=target_user.photo.big_file_id,
            file_name=os.path.join(TEMP_DIR, "")
        )
        
        if not file_path:
             return await progress_message.edit("Could not download profile media.", del_in=ERROR_VISIBLE_DURATION)

        caption_text = f"Profile media for: {target_user.mention}"

        # Check the downloaded file's extension to determine the type
        if str(file_path).endswith(".mp4"):
            await bot.send_video(
                chat_id=message.chat.id,
                video=file_path,
                caption=caption_text,
                reply_parameters=ReplyParameters(message_id=message.id)
            )
        else:
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=file_path,
                caption=caption_text,
                reply_parameters=ReplyParameters(message_id=message.id)
            )
        
        await progress_message.delete()
        await message.delete()

    except AttributeError:
        # This happens if the user has no profile photo at all
        await progress_message.edit("This user has no profile picture or video.", del_in=ERROR_VISIBLE_DURATION)
    except Exception as e:
        error_text = f"<b>Error:</b> Could not fetch profile media.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
    finally:
        # Clean up the downloaded file
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
