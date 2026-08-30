import os
import html
import shutil
from pyrogram.errors import UserNotParticipant
from pyrogram.enums import ChatType, UserStatus, ChatMemberStatus
from pyrogram.types import Message, User, LinkPreviewOptions, ReplyParameters

from app import BOT, bot

from app.modules.settings import TINY_TIMEOUT, SMALL_TIMEOUT, MEDIUM_TIMEOUT, LONG_TIMEOUT, VERY_LONG_TIMEOUT, LARGE_TIMEOUT

TEMP_INFO_DIR = "temp_info_photos/"

def safe_escape(text: str) -> str:
    return html.escape(str(text)) if text else ""

def get_user_status(user: User) -> str:
    if not user.status:
        return "N/A"

    status_map = {
        UserStatus.ONLINE: "Online",
        UserStatus.OFFLINE: user.last_online_date.strftime('%d %b %Y, %H:%M') if user.last_online_date else "Offline",
        UserStatus.RECENTLY: "Recently",
        UserStatus.LAST_WEEK: "Within a week",
        UserStatus.LAST_MONTH: "Within a month",
        UserStatus.LONG_AGO: "Long ago"
    }
    return status_map.get(user.status, str(user.status))

async def format_user_info(user: User, is_full: bool, message: Message) -> tuple[str, str | None]:
    full_chat_info = await bot.get_chat(user.id)

    if is_full:
        info_lines = ["<b>User Info:</b>"]
        info_lines.extend([f"• <b>ID:</b> <code>{user.id}</code>", f"• <b>First Name:</b> {safe_escape(user.first_name)}"])
        if user.last_name: info_lines.append(f"• <b>Last Name:</b> {safe_escape(user.last_name)}")
        if user.username: info_lines.append(f"• <b>Username:</b> @{user.username}")
        if user.dc_id: info_lines.append(f"• <b>DC ID:</b> {user.dc_id}")
        if user.language_code: info_lines.append(f"• <b>Language:</b> {user.language_code}")

        flags = ["Bot 🤖"] if user.is_bot else []
        if user.is_verified: flags.append("Verified ✅")
        if user.is_scam: flags.append("Scam ‼️")
        if user.is_premium: flags.append("Premium ✨")
        if flags: info_lines.append(f"• <b>Flags:</b> {', '.join(flags)}")

        info_lines.append(f"• <b>Last Seen:</b> {get_user_status(user)}")

        if full_chat_info.bio: info_lines.append(f"• <b>Bio:</b> {safe_escape(full_chat_info.bio)}")

        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            try:
                member = await bot.get_chat_member(message.chat.id, user.id)
                if member:
                    info_lines.append("\n<b>Group Status:</b>")
                    group_details = []
                    status_map = {ChatMemberStatus.OWNER: "Owner", ChatMemberStatus.ADMINISTRATOR: "Administrator", ChatMemberStatus.MEMBER: "Member", ChatMemberStatus.RESTRICTED: "Restricted", ChatMemberStatus.LEFT: "Not in chat", ChatMemberStatus.BANNED: "Banned"}
                    status_str = status_map.get(member.status, "Unknown")
                    if member.custom_title: status_str += f" (Title: {safe_escape(member.custom_title)})"
                    group_details.append(f"• <b>Status:</b> {status_str}")
                    if member.joined_date: group_details.append(f"• <b>Joined:</b> {member.joined_date.strftime('%d %b %Y, %H:%M UTC')}")
                    if member.promoted_by: group_details.append(f"• <b>Promoted By:</b> {member.promoted_by.mention}")
                    if member.privileges:
                        perms = member.privileges
                        perm_list = [("– Manage Chat", perms.can_manage_chat), ("– Delete Messages", perms.can_delete_messages), ("– Manage Video Chats", perms.can_manage_video_chats), ("– Restrict Members", perms.can_restrict_members), ("– Change Info", perms.can_change_info), ("– Invite Users", perms.can_invite_users), ("– Pin Messages", perms.can_pin_messages), ("– Post Stories", perms.can_post_stories), ("– Edit Stories", perms.can_edit_stories), ("– Delete Stories", perms.can_delete_stories)]
                        granted_perms = [text for text, has_perm in perm_list if has_perm]
                        if granted_perms: group_details.append("• <b>Permissions:</b>\n" + "\n".join(granted_perms))
                    info_lines.append(f"<blockquote expandable>{'\n'.join(group_details)}</blockquote>")
            except UserNotParticipant:
                info_lines.append("\n<b>Group Info:</b>")
                group_details = [f"• <b>Status:</b> Not in chat"]
                info_lines.append(f"<blockquote expandable>{'\n'.join(group_details)}</blockquote>")
            except Exception: pass

        info_lines.append(f"\n<b>Permalink:</b> <a href='tg://user?id={user.id}'>Click Here</a>")

    else:
        info_lines = ["<b>User info:</b>", f"• <b>ID:</b> <code>{user.id}</code>", f"• <b>First Name:</b> {safe_escape(user.first_name)}"]
        if user.last_name: info_lines.append(f"• <b>Last Name:</b> {safe_escape(user.last_name)}")
        if user.username: info_lines.append(f"• <b>Username:</b> @{user.username}")
        try:
            if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                member = await bot.get_chat_member(message.chat.id, user.id)
                status_map = {ChatMemberStatus.OWNER: "Owner", ChatMemberStatus.ADMINISTRATOR: "Admin", ChatMemberStatus.MEMBER: "Member", ChatMemberStatus.RESTRICTED: "Restricted", ChatMemberStatus.LEFT: "Not in chat", ChatMemberStatus.BANNED: "Banned"}
                if member.status in status_map:
                    status_str = status_map.get(member.status)
                    info_lines.append(f"• <b>Status:</b> {status_str}")
        except UserNotParticipant:
            info_lines.append(f"• <b>Status:</b> Not in chat")
        except Exception: pass
        info_lines.append(f"\n<b>Permalink:</b> {user.mention('Click Here')}")

    photo_id = full_chat_info.photo.big_file_id if is_full and full_chat_info.photo else None
    return "\n".join(info_lines), photo_id

@bot.add_cmd(cmd=["info", "whois"])
async def info_handler(bot: BOT, message: Message):
    progress_msg = await message.reply("<code>Fetching user information...</code>")

    is_full_mode = "-full" in message.text.split()
    target_identifier = message.input.replace("-full", "").strip() if message.input else None

    if not target_identifier:
        if message.replied and message.replied.from_user:
            target_identifier = message.replied.from_user.id
        else:
            target_identifier = message.from_user.id
    try:
        target_user = await bot.get_users(target_identifier)
        final_text, photo_id = await format_user_info(target_user, is_full_mode, message)

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
                await progress_msg.delete()
            finally:
                if os.path.exists(photo_path):
                    shutil.rmtree(TEMP_INFO_DIR, ignore_errors=True)
        else:
            await progress_msg.edit(
                final_text,
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )

    except Exception as e:
        await progress_msg.edit(f"<b>Error:</b> Could not find the specified user.\n<code>{safe_escape(str(e))}</code>", del_in=LONG_TIMEOUT)

# Special Thanks to MoonUB team for code and idea
# Moon Userbot Organization
# https://github.com/The-MoonTg-project/Moon-Userbot/
@bot.add_cmd(cmd=["infop"])
async def infop_handler(bot: BOT, message: Message):
    progress_msg = await message.reply("<code>Fetching user information...</code>")

    target_identifier = message.input.strip() if getattr(message, "input", None) else None

    if not target_identifier:
        if message.replied and message.replied.from_user:
            target_identifier = message.replied.from_user.id
        else:
            target_identifier = message.from_user.id

    try:
        peer = await bot.resolve_peer(target_identifier)
        response = await bot.invoke(functions.users.GetFullUser(id=peer))

        user = response.users[0]
        full_user = response.full_user

        username = f"@{user.username}" if getattr(user, 'username', None) else "N/A"
        name = getattr(user, 'first_name', '')
        if getattr(user, 'last_name', None):
            name += f" {user.last_name}"

        bio = getattr(full_user, 'about', "N/A")

        await bot.unblock_user("@creationdatebot")
        try:
            creation_response = await interact_with(
                await bot.send_message("creationdatebot", f"/id {user.id}")
            )
            creation_date = creation_response.text
            interact_with_to_delete.clear()
        except Exception:
            creation_date = "Unknown"

        info_text = (
            f"|=Username: {username}\n"
            f"|-Id: {user.id}\n"
            f"|-Account creation date: {creation_date}\n"
            f"|-Bot: {getattr(user, 'bot', False)}\n"
            f"|-Scam: {getattr(user, 'scam', False)}\n"
            f"|-Name: {name}\n"
            f"|-Deleted: {getattr(user, 'deleted', False)}\n"
            f"|-BIO: {bio}\n"
            f"|-Contact: {getattr(user, 'contact', False)}\n"
            f"|-Can pin message: {getattr(full_user, 'can_pin_message', False)}\n"
            f"|-Mutual contact: {getattr(user, 'mutual_contact', False)}\n"
            f"|-Access hash: {getattr(user, 'access_hash', 'Hidden')}\n"
            f"|-Restricted: {getattr(user, 'restricted', False)}\n"
            f"|-Verified: {getattr(user, 'verified', False)}\n"
            f"|-Phone calls available: {getattr(full_user, 'phone_calls_available', False)}\n"
            f"|-Phone calls private: {getattr(full_user, 'phone_calls_private', False)}\n"
            f"|-Blocked: {getattr(full_user, 'blocked', False)}"
        )

        await progress_msg.edit(
            info_text,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )

    except Exception as e:
        await progress_msg.edit(
            f"<b>Error:</b> Could not find the specified user.\n<code>{safe_escape(str(e))}</code>",
            del_in=LONG_TIMEOUT
        )
