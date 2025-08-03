import os
import html
import shutil
from pyrogram.enums import ChatType, UserStatus
from pyrogram.types import Chat, Message, User, LinkPreviewOptions, ReplyParameters

from app import BOT, bot

TEMP_INFO_DIR = "temp_info_photos/"

def safe_escape(text: str) -> str:
    escaped_text = html.escape(str(text))
    return escaped_text.replace("&#x27;", "’")

def get_user_status(user: User) -> str:
    """Formats the user's online status into a readable string."""
    if not user.status:
        return "<i>Unknown</i>"
    
    last_seen = user.last_online_date.strftime('%Y-%m-%d %H:%M') if user.last_online_date else 'unknown'
    status_map = {
        UserStatus.ONLINE: "🟢 Online",
        UserStatus.OFFLINE: f"🔴 Offline (Last seen: {last_seen})",
        UserStatus.RECENTLY: "🟠 Last seen recently",
        UserStatus.LAST_WEEK: "🟡 Last seen last week",
        UserStatus.LAST_MONTH: "⚪️ Last seen last month"
    }
    return status_map.get(user.status, "<i>Unknown status</i>")

async def format_user_info(user: User) -> tuple[str, str | None]:
    """Formats the information for a user."""
    full_chat_info = await bot.get_chat(user.id)
    info_lines = ["<b>User Info:</b>"]
    
    full_name = user.first_name
    if user.last_name:
        full_name += f" {user.last_name}"
    info_lines.append(f"• <b>Name:</b> {safe_escape(full_name)}")
    info_lines.append(f"• <b>ID:</b> <code>{user.id}</code>")

    if user.username:
        info_lines.append(f"• <b>Username:</b> @{user.username}")
        info_lines.append(f"• <b>Permalink:</b> <a href='https://t.me/{user.username}'>{user.username}</a>")
    else:
        info_lines.append(f"• <b>Permalink:</b> {user.mention(style='md')}")

    info_lines.append(f"• <b>Status:</b> {get_user_status(user)}")
    if full_chat_info.bio:
        info_lines.append(f"• <b>Bio:</b> {safe_escape(full_chat_info.bio)}")
    info_lines.append(f"• <b>Type:</b> {'Bot 🤖' if user.is_bot else 'User 👤'}")
        
    flags = [flag for c, flag in [(user.is_verified, "Verified ✅"), (user.is_scam, "Scam ‼️"), (user.is_premium, "Premium ✨")] if c]
    if flags:
        info_lines.append(f"• <b>Flags:</b> {', '.join(flags)}")
    if user.dc_id:
        info_lines.append(f"• <b>Data Center:</b> {user.dc_id}")
    try:
        common_chats_count = await bot.get_common_chats_count(user.id)
        info_lines.append(f"• <b>Common Groups:</b> {common_chats_count}")
    except Exception:
        pass

    photo_id = full_chat_info.photo.big_file_id if full_chat_info.photo else None
    return "\n".join(info_lines), photo_id

async def format_chat_info(chat: Chat) -> tuple[str, str | None]:
    """Formats the information for a group or channel."""
    info_lines = ["<b>Chat Info:</b>"]
    info_lines.append(f"• <b>Title:</b> {safe_escape(chat.title)}")
    info_lines.append(f"• <b>ID:</b> <code>{chat.id}</code>")

    type_map = {ChatType.GROUP: "Group 👥", ChatType.SUPERGROUP: "Supergroup 👥", ChatType.CHANNEL: "Channel 📢"}
    info_lines.append(f"• <b>Type:</b> {type_map.get(chat.type, '<i>Unknown</i>')}")

    if chat.username:
        info_lines.append(f"• <b>Username:</b> @{chat.username}")
        info_lines.append(f"• <b>Permalink:</b> <a href='https://t.me/{chat.username}'>{chat.username}</a>")
    if chat.description:
        desc = chat.description
        info_lines.append(f"• <b>Description:</b> {safe_escape(desc[:200] + '...' if len(desc) > 200 else desc)}")
    if chat.members_count:
        info_lines.append(f"• <b>Members:</b> {chat.members_count}")

    flags = [flag for c, flag in [(chat.is_verified, "Verified ✅"), (chat.is_scam, "Scam ‼️"), (chat.is_restricted, "Restricted 🔞")] if c]
    if flags:
        info_lines.append(f"• <b>Flags:</b> {', '.join(flags)}")
    if chat.dc_id:
        info_lines.append(f"• <b>Data Center:</b> {chat.dc_id}")
    if chat.linked_chat:
        info_lines.append(f"• <b>Linked Chat ID:</b> <code>{chat.linked_chat.id}</code>")

    photo_id = chat.photo.big_file_id if chat.photo else None
    return "\n".join(info_lines), photo_id

@bot.add_cmd(cmd=["info", "whois"])
async def info_handler(bot: BOT, message: Message):
    progress: Message = await message.reply("<code>Fetching information...</code>")

    target_identifier = None
    if message.input:
        target_identifier = message.input.strip()
    elif message.replied:
        target_identifier = message.replied.from_user.id if message.replied.from_user else message.replied.chat.id
    else:
        target_identifier = "me"

    final_text, photo_id = "", None
    
    try:
        target_chat = await bot.get_chat(target_identifier)
        
        if target_chat.type == ChatType.PRIVATE:
            target_user = await bot.get_users(target_chat.id)
            final_text, photo_id = await format_user_info(target_user)
        else:
            final_text, photo_id = await format_chat_info(target_chat)

    except Exception as e:
        return await progress.edit(f"<b>Error:</b> Could not find the specified entity.\n<code>{safe_escape(str(e))}</code>")

    if photo_id:
        photo_path = ""
        try:
            os.makedirs(TEMP_INFO_DIR, exist_ok=True)
            photo_path = await bot.download_media(photo_id, file_name=TEMP_INFO_DIR)
            
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=photo_path,
                caption=final_text,
                reply_parameters=ReplyParameters(message_id=message.id)
            )
            await progress.delete()
        finally:
            if os.path.exists(photo_path):
                shutil.rmtree(TEMP_INFO_DIR, ignore_errors=True)
    else:
        await message.reply(
            final_text,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        await progress.delete()
