import html
from datetime import datetime

from pyrogram.enums import UserStatus
from pyrogram.types import LinkPreviewOptions, Message, User

from app import BOT, bot

def safe_escape(text: str) -> str:
    escaped_text = html.escape(str(text))
    return escaped_text.replace("'", "’")

def get_user_status(user: User) -> str:
    if not user.status:
        return "<i>Unknown</i>"
    
    if user.status == UserStatus.ONLINE:
        return "🟢 Online"
    if user.status == UserStatus.OFFLINE:
        return f"🔴 Offline (Last seen: {user.last_online_date.strftime('%Y-%m-%d %H:%M')})"
    if user.status == UserStatus.RECENTLY:
        return "🟠 Last seen recently"
    if user.status == UserStatus.LAST_WEEK:
        return "🟡 Last seen last week"
    if user.status == UserStatus.LAST_MONTH:
        return "⚪️ Last seen last month"
    
    return "<i>Unknown status</i>"


@bot.add_cmd(cmd=["info", "whois", "userinfo"])
async def info_handler(bot: BOT, message: Message):
    progress: Message = await message.reply("Fetching user information...")

    target_user: User | None = None
    
    if message.input:
        target_identifier = message.input
    elif message.replied:
        target_identifier = message.replied.from_user.id
    else:
        target_identifier = message.from_user.id

    try:
        target_user = await bot.get_users(target_identifier)
        full_chat_info = await bot.get_chat(target_user.id)
    except Exception as e:
        return await progress.edit(
            f"<b>Error:</b> Could not find the specified user.\n<code>{safe_escape(str(e))}</code>"
        )

    info_lines = ["<b>User Info:</b>"]
    
    full_name = target_user.first_name
    if target_user.last_name:
        full_name += f" {target_user.last_name}"
    info_lines.append(f"• <b>Name:</b> {safe_escape(full_name)}")
    info_lines.append(f"• <b>ID:</b> <code>{target_user.id}</code>")

    if target_user.username:
        info_lines.append(f"• <b>Username:</b> @{target_user.username}")
        info_lines.append(f"• <b>Permalink:</b> <a href='https://t.me/{target_user.username}'>t.me/{target_user.username}</a>")
    else:
        info_lines.append(f"• <b>Permalink:</b> {target_user.mention(style='md')}")

    info_lines.append(f"• <b>Status:</b> {get_user_status(target_user)}")

    if full_chat_info.bio:
        info_lines.append(f"• <b>Bio:</b> {safe_escape(full_chat_info.bio)}")
        
    if target_user.is_bot:
        info_lines.append("• <b>Type:</b> Bot 🤖")
    else:
        info_lines.append("• <b>Type:</b> User 👤")
        
    flags = []
    if target_user.is_verified:
        flags.append("Verified ✅")
    if target_user.is_scam:
        flags.append("Scam ‼️")
    if target_user.is_premium:
        flags.append("Premium ✨")
    if flags:
        info_lines.append(f"• <b>Flags:</b> {', '.join(flags)}")

    if target_user.dc_id:
        info_lines.append(f"• <b>Data Center:</b> {target_user.dc_id}")
        
    try:
        common_chats_count = len(await target_user.get_common_chats())
        info_lines.append(f"• <b>Common Groups:</b> {common_chats_count}")
    except Exception:
        pass

    final_text = "\n".join(info_lines)
    
    photo_to_send = None
    try:
        async for photo in bot.get_chat_photos(target_user.id, limit=1):
            photo_to_send = photo.file_id
    except Exception:
        pass
    
    if photo_to_send:
        await progress.delete()
        await message.reply_photo(
            photo=photo_to_send,
            caption=final_text
        )
    else:
        await progress.edit(
            final_text,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
