import html
from pyrogram.enums import ChatType
from pyrogram.types import Chat, Message, LinkPreviewOptions

from app import BOT, bot

def safe_escape(text: str) -> str:
    escaped_text = html.escape(str(text))
    return escaped_text.replace("&#x27;", "’")

@bot.add_cmd(cmd=["chatinfo", "cinfo"])
async def chat_info_handler(bot: BOT, message: Message):
    """
    CMD: CHATINFO / CINFO
    INFO: Gets detailed information about a chat, channel, or group.
    USAGE:
        .chatinfo (in the target chat)
        .chatinfo [id/username]
    """
    progress: Message = await message.reply("<code>Fetching chat information...</code>")

    target_identifier = message.chat.id
    if message.input:
        target_identifier = message.input.strip()

    try:
        chat_info: Chat = await bot.get_chat(target_identifier)
    except Exception as e:
        return await progress.edit(
            f"<b>Error:</b> Could not find the specified chat.\n<code>{safe_escape(str(e))}</code>"
        )

    info_lines = ["<b>Chat Info:</b>"]
    
    info_lines.append(f"• <b>Title:</b> {safe_escape(chat_info.title)}")
    info_lines.append(f"• <b>ID:</b> <code>{chat_info.id}</code>")

    chat_type = "<i>Unknown</i>"
    if chat_info.type == ChatType.PRIVATE:
        chat_type = "Private Chat 👤"
    elif chat_info.type == ChatType.GROUP:
        chat_type = "Group 👥"
    elif chat_info.type == ChatType.SUPERGROUP:
        chat_type = "Supergroup 👥"
    elif chat_info.type == ChatType.CHANNEL:
        chat_type = "Channel 📢"
    
    info_lines.append(f"• <b>Type:</b> {chat_type}")

    if chat_info.username:
        info_lines.append(f"• <b>Username:</b> @{chat_info.username}")
        info_lines.append(f"• <b>Permalink:</b> <a href='https://t.me/{chat_info.username}'>t.me/{chat_info.username}</a>")
    
    if chat_info.description:
        desc = chat_info.description
        if len(desc) > 200:
            desc = desc[:200] + "..."
        info_lines.append(f"• <b>Description:</b> {safe_escape(desc)}")
        
    if chat_info.members_count:
        info_lines.append(f"• <b>Members:</b> {chat_info.members_count}")

    flags = []
    if chat_info.is_verified:
        flags.append("Verified ✅")
    if chat_info.is_scam:
        flags.append("Scam ‼️")
    if chat_info.is_restricted:
        flags.append("Restricted 🔞")
    if flags:
        info_lines.append(f"• <b>Flags:</b> {', '.join(flags)}")

    if chat_info.dc_id:
        info_lines.append(f"• <b>Data Center:</b> {chat_info.dc_id}")
        
    if chat_info.linked_chat:
        info_lines.append(f"• <b>Linked Chat ID:</b> <code>{chat_info.linked_chat.id}</code>")

    final_text = "\n".join(info_lines)
    
    photo_to_send = None
    try:
        if chat_info.photo:
            photo_to_send = chat_info.photo.big_file_id
    except Exception:
        pass
    
    if photo_to_send:
        await progress.delete()
        await message.reply_photo(
            photo=photo_to_send,
            caption=final_text,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    else:
        await progress.edit(
            final_text,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
