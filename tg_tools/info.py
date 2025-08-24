import os
import html
import shutil
from datetime import datetime
from pyrogram.enums import ChatType, UserStatus, ChatMemberStatus
from pyrogram.types import Chat, Message, User, LinkPreviewOptions, ReplyParameters, ChatPrivileges

from app import BOT, bot

TEMP_INFO_DIR = "temp_info_photos/"

def safe_escape(text: str) -> str:
    """Safely escapes HTML special characters."""
    return html.escape(str(text)) if text else ""

def get_user_status(user: User) -> str:
    """Formats the user's online status into a readable string."""
    if not user.status or not user.last_online_date:
        return "Hidden"
    
    status_map = {
        UserStatus.ONLINE: "Online",
        UserStatus.OFFLINE: user.last_online_date.strftime('%d %b %Y, %H:%M'),
        UserStatus.RECENTLY: "Recently",
        UserStatus.LAST_WEEK: "Within a week",
        UserStatus.LAST_MONTH: "Within a month"
    }
    return status_map.get(user.status, "Hidden")

async def format_user_info_text(user: User, message: Message) -> tuple[str, str | None]:
    """Formats the complete information for a user, including contextual group info."""
    
    full_chat_info = await bot.get_chat(user.id)
    
    flags = ["Bot 🤖"] if user.is_bot else []
    if user.is_verified: flags.append("Verified ✅")
    if user.is_scam: flags.append("Scam ‼️")
    if user.is_premium: flags.append("Premium ✨")
    
    info_lines = [
        "<b>👤 User Info</b>",
        f"• <b>ID:</b> <code>{user.id}</code>",
        f"• <b>First Name:</b> {safe_escape(user.first_name)}",
    ]
    if user.username:
        info_lines.append(f"• <b>Username:</b> @{user.username}")
    if user.dc_id:
        info_lines.append(f"• <b>DC ID:</b> {user.dc_id}")
    if user.language_code:
        info_lines.append(f"• <b>Language:</b> {user.language_code}")
    if flags:
        info_lines.append(f"• <b>Flags:</b> {', '.join(flags)}")
    
    info_lines.append(f"• <b>Last Seen:</b> {get_user_status(user)}")
    
    if full_chat_info.bio:
        info_lines.append(f"• <b>Bio:</b> {safe_escape(full_chat_info.bio)}")

    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        try:
            member = await bot.get_chat_member(message.chat.id, user.id)
            if member:
                group_lines = ["\n<b>👥 Group Info:</b>"]
                
                status_map = {
                    ChatMemberStatus.OWNER: "Creator",
                    ChatMemberStatus.ADMINISTRATOR: "Administrator",
                    ChatMemberStatus.MEMBER: "Member",
                    ChatMemberStatus.RESTRICTED: "Restricted",
                    ChatMemberStatus.LEFT: "Left",
                    ChatMemberStatus.BANNED: "Banned"
                }
                status_str = status_map.get(member.status, "Unknown")
                if member.custom_title:
                    status_str += f" (Title: {safe_escape(member.custom_title)})"
                group_lines.append(f"• <b>Status:</b> {status_str}")

                if member.joined_date:
                    group_lines.append(f"• <b>Joined:</b> {member.joined_date.strftime('%d %b %Y, %H:%M UTC')}")
                if member.promoted_by:
                    group_lines.append(f"• <b>Promoted By:</b> {member.promoted_by.mention}")

                if member.privileges:
                    perms = member.privileges
                    perm_list = [
                        ("– Manage Chat", perms.can_manage_chat),
                        ("– Delete Messages", perms.can_delete_messages),
                        ("– Manage Video Chats", perms.can_manage_video_chats),
                        ("– Restrict Members", perms.can_restrict_members),
                        ("– Change Info", perms.can_change_info),
                        ("– Invite Users", perms.can_invite_users),
                        ("– Pin Messages", perms.can_pin_messages),
                        ("– Post Messages", perms.can_post_messages),
                        ("– Edit Messages", perms.can_edit_messages),
                        ("– Post Stories", perms.can_post_stories),
                        ("– Edit Stories", perms.can_edit_stories),
                        ("– Delete Stories", perms.can_delete_stories),
                        ("– Manage Topics", perms.can_manage_topics),
                    ]
                    granted_perms = [text for text, has_perm in perm_list if has_perm]
                    if granted_perms:
                        group_lines.append("• <b>Permissions:</b>\n" + "\n".join(granted_perms))

                info_lines.append(f"<blockquote>{\"\n\".join(group_lines)}</blockquote>")
        except Exception:
            pass

    info_lines.append(f"\n🔗 <b>Profile Link:</b> <a href='tg://user?id={user.id}'>Click Here</a>")

    photo_id = full_chat_info.photo.big_file_id if full_chat_info.photo else None
    return "\n".join(info_lines), photo_id

@bot.add_cmd(cmd=["info", "whois"])
async def info_handler(bot: BOT, message: Message):
    progress: Message = await message.reply("<code>Fetching information...</code>")

    target_identifier = None
    if message.input:
        target_identifier = message.input.strip()
    elif message.replied and message.replied.from_user:
        target_identifier = message.replied.from_user.id
    else:
        target_identifier = "me"

    final_text, photo_id = "", None
    try:
        target_user = await bot.get_users(target_identifier)
        final_text, photo_id = await format_user_info_text(target_user, message)
    except Exception as e:
        return await progress.edit(f"<b>Error:</b> Could not find the specified user.\n<code>{safe_escape(str(e))}</code>")
    
    await progress.delete()
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
        finally:
            if os.path.exists(photo_path):
                shutil.rmtree(TEMP_INFO_DIR, ignore_errors=True)
    else:
        await message.reply(
            final_text,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
