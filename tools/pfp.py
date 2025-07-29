import html
from pyrogram.types import Message, User, InputMediaPhoto, InputMediaVideo

from app import BOT, bot

ERROR_VISIBLE_DURATION = 8

@bot.add_cmd(cmd="pfp")
async def pfp_handler(bot: BOT, message: Message):
    """
    CMD: PFP
    INFO: Fetches a user's profile pictures and videos.
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
        photos = await bot.get_chat_photos(target_user.id)
        
        if not photos:
            return await progress_message.edit("This user has no profile pictures or videos.", del_in=ERROR_VISIBLE_DURATION)

        media_to_send = []
        for photo in photos:
            # Check if it's a profile video
            if photo.video_file_id:
                media_to_send.append(InputMediaVideo(photo.video_file_id))
            # Otherwise, it's a static photo
            else:
                media_to_send.append(InputMediaPhoto(photo.file_id))
        
        # Telegram's send_media_group has a limit of 10 items per album
        if not media_to_send:
             return await progress_message.edit("Could not retrieve any profile media.", del_in=ERROR_VISIBLE_DURATION)

        await progress_message.edit(f"<code>Found {len(media_to_send)} items. Sending the first 10 as an album...</code>")

        await bot.send_media_group(
            chat_id=message.chat.id,
            media=media_to_send[:10],
            reply_to_message_id=message.id
        )
        
        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not fetch profile media.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
