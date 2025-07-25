import asyncio

from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait, UserAdminInvalid
from pyrogram.types import User
from ub_core.utils.helpers import get_name

from app import BOT, Config, Message, bot, extra_config

GBAN_TASK_LOCK = asyncio.Lock()


@bot.add_cmd(cmd=["gban", "gbanp"])
async def global_ban(bot: BOT, message: Message):
    """
    CMD: GBAN / GBANP
    INFO: Globally bans a user in all chats where the bot is an admin.
    USAGE:
        .gban <user_id/reply> [reason]
        .gbanp <reply to a proof> [reason]
    """
    progress: Message = await message.reply("❯")
    
    extracted_info = await get_user_reason(message=message, progress=progress)
    if not extracted_info:
        return

    user_id, user_mention, reason = extracted_info

    if user_id in [Config.OWNER_ID, *Config.SUPERUSERS, *Config.SUDO_USERS]:
        await progress.edit("Cannot gban the owner or sudo users.")
        return

    proof_str: str = ""
    if message.cmd == "gbanp":
        if not message.replied:
            await progress.edit("Reply to a message to be used as proof.")
            return
        proof = await message.replied.forward(extra_config.FBAN_LOG_CHANNEL)
        proof_str = f"\n{ {proof.link} }"

    reason_with_proof = f"{reason}{proof_str}"

    await perform_global_task(
        user_id=user_id,
        user_mention=user_mention,
        reason=reason_with_proof,
        progress=progress,
        message=message,
        task_type="Gban",
    )


@bot.add_cmd(cmd="ungban")
async def un_global_ban(bot: BOT, message: Message):
    """
    CMD: UNGBAN
    INFO: Globally unbans a user from all chats.
    USAGE:
        .ungban <user_id/reply> [reason]
    """
    progress: Message = await message.reply("❯")
    
    extracted_info = await get_user_reason(message=message, progress=progress)
    if not extracted_info:
        return

    user_id, user_mention, reason = extracted_info

    await perform_global_task(
        user_id=user_id,
        user_mention=user_mention,
        reason=reason,
        progress=progress,
        message=message,
        task_type="Un-Gban",
    )


async def get_user_reason(message: Message, progress: Message) -> tuple[int, str, str] | None:
    """Shared function to extract user and reason."""
    user, reason = await message.extract_user_n_reason()
    if isinstance(user, str):
        await progress.edit(user)
        return None
    if not isinstance(user, User):
        user_id = user
        user_mention = f"<a href='tg://user?id={user_id}'>{user_id}</a>"
    else:
        user_id = user.id
        user_mention = user.mention
    return user_id, user_mention, reason


async def perform_global_task(
    user_id: int,
    user_mention: str,
    reason: str,
    progress: Message,
    message: Message,
    task_type: str,
):
    """Performs the gban/ungban task by iterating through all of the bot's chats."""
    async with GBAN_TASK_LOCK:
        await progress.edit("❯❯")

        action_count: int = 0
        failed_count: int = 0
        total_chats: int = 0

        async for dialog in bot.get_dialogs():
            if dialog.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
                continue
            
            total_chats += 1
            chat_id = dialog.chat.id

            try:
                if task_type == "Gban":
                    await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                else:
                    await bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
                action_count += 1
                await asyncio.sleep(0.1)

            except FloodWait as e:
                await bot.log_text(f"#GBAN #FLOODWAIT\nSleeping for {e.value}s.")
                await asyncio.sleep(e.value + 2)
                try:
                    if task_type == "Gban":
                        await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                    else:
                        await bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
                    action_count += 1
                except Exception:
                    failed_count += 1
            except (UserAdminInvalid, Exception):
                failed_count += 1
        
        if total_chats == 0:
            await progress.edit("The bot isn't in any groups.")
            return
        
        action_past_tense = task_type.replace("-", "") + "ned"

        resp_str = (
            f"❯❯❯ <b>{action_past_tense}</b> {user_mention}"
            f"\n<b>ID</b>: {user_id}"
            f"\n<b>Reason</b>: {reason}"
            f"\n<b>Initiated in</b>: {message.chat.title or 'PM'}"
        )

        if failed_count > 0:
            resp_str += f"\n<b>Failed</b> in: {failed_count}/{total_chats} groups."
        else:
            resp_str += f"\n<b>Status</b>: {action_past_tense} in <b>{total_chats}</b> groups."

        if not message.is_from_owner:
            resp_str += f"\n\n<b>By</b>: {get_name(message.from_user)}"
        
        await bot.send_message(
            chat_id=extra_config.FBAN_LOG_CHANNEL, text=resp_str, disable_preview=True
        )

        await progress.edit(text=resp_str, del_in=5, block=True, disable_preview=True)
