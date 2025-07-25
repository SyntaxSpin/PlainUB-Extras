import asyncio

from pyrogram.types import User
from ub_core.utils.helpers import get_name

from app import BOT, Config, CustomDB, Message, bot, extra_config

ABAN_TASK_LOCK = asyncio.Lock()

FBAN_DB = CustomDB["FED_LIST"]
GBAN_DB = CustomDB["GBAN_CHAT_LIST"]


@bot.add_cmd(cmd=["aban", "abanp"])
async def all_ban_handler(bot: BOT, message: Message):
    """
    CMD: ABAN / ABANP
    INFO: Executes FBAN and GBAN simultaneously.
    USAGE:
        .aban <user_id/reply> [reason]
        .abanp <reply to a proof> [reason]
    """
    progress: Message = await message.reply("❯")

    extracted_info = await get_user_reason(message=message, progress=progress)
    if not extracted_info:
        await progress.edit("Failed to extract user info.")
        return
    
    user, reason = await message.extract_user_n_reason()
    if isinstance(user, str):
        return await progress.edit(user)
    
    if not isinstance(user, User):
        user_id = user
        user_mention = f"<a href='tg://user?id={user_id}'>{user_id}</a>"
    else:
        user_id = user.id
        user_mention = user.mention

    if user_id in [Config.OWNER_ID, *Config.SUPERUSERS, *Config.SUDO_USERS]:
        return await progress.edit("Cannot use All-Ban on the owner or sudo users.")

    proof_str: str = ""
    if message.cmd == "abanp":
        if not message.replied:
            return await progress.edit("Reply to a message with the proof.")
        proof = await message.replied.forward(extra_config.FBAN_LOG_CHANNEL)
        proof_str = f"\n{ {proof.link} }"

    reason_with_proof = f"{reason}{proof_str}"

    await perform_all_ban_task(
        user_id=user_id,
        user_mention=user_mention,
        reason=reason_with_proof,
        progress=progress,
        message=message,
        task_type="AllBan",
        fban_cmd_str="fban",
        gban_cmd_str="gban"
    )


@bot.add_cmd(cmd="unaban")
async def all_unban_handler(bot: BOT, message: Message):
    """
    CMD: UNABAN
    INFO: Executes UN-FBAN and UN-GBAN simultaneously.
    USAGE:
        .unaban <user_id/reply> [reason]
    """
    progress: Message = await message.reply("❯")

    extracted_info = await get_user_reason(message=message, progress=progress)
    if not extracted_info:
        await progress.edit("Failed to extract user info.")
        return
    
    user, reason = await message.extract_user_n_reason()
    if isinstance(user, str):
        return await progress.edit(user)
    
    if not isinstance(user, User):
        user_id = user
        user_mention = f"<a href='tg://user?id={user_id}'>{user_id}</a>"
    else:
        user_id = user.id
        user_mention = user.mention

    await perform_all_ban_task(
        user_id=user_id,
        user_mention=user_mention,
        reason=reason,
        progress=progress,
        message=message,
        task_type="All-Unban",
        fban_cmd_str="unfban",
        gban_cmd_str="ungban"
    )

async def get_user_reason(message: Message, progress: Message) -> tuple[int, str, str] | None:
    """Standardized helper function to extract user and reason."""
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

async def perform_all_ban_task(
    user_id: int, user_mention: str, reason: str, progress: Message, message: Message,
    task_type: str, fban_cmd_str: str, gban_cmd_str: str
):
    async with ABAN_TASK_LOCK:
        await progress.edit("❯❯")

        fban_total, fban_failed_list = await _perform_fban_for_aban(user_id, reason, fban_cmd_str)
        gban_total, gban_failed_list = await _perform_gban_for_aban(user_id, reason, gban_cmd_str)

    if fban_total == 0:
        await progress.edit("No Feds are configured. Use .fban command or add a fed with .addf command.")
        return

    if gban_total == 0:
        await progress.edit("No Gban bot chats are configured. Use .gban command or add a chat with .addg command.")
        return

        action_past_tense = task_type.replace("-", "") + "ned"

        resp_str = (
            f"❯❯❯ <b>{action_past_tense}</b> {user_mention}"
            f"\n<b>ID</b>: {user_id}"
            f"\n<b>Reason</b>: {reason}"
            f"\n<b>Initiated in</b>: {message.chat.title or 'PM'}"
        )

        success_parts = []
        failure_parts = []

        if fban_total > 0:
            if not fban_failed_list:
                success_parts.append(f"Fbanned in <b>{fban_total}</b> feds.")
            else:
                failure_parts.append(f"Fban failed in {len(fban_failed_list)}/{fban_total} feds")

        if gban_total > 0:
            if not gban_failed_list:
                success_parts.append(f"Gbanned in <b>{gban_total}</b> chats")
            else:
                failure_parts.append(f"Gban failed in {len(gban_failed_list)}/{gban_total} bots.")

        if failure_parts:
            resp_str += "\n<b>Failed</b>: " + " and ".join(failure_parts) + "."
        
        if success_parts:
            status_header = "Success" if failure_parts else "Status"
            resp_str += f"\n<b>{status_header}</b>: " + " and ".join(success_parts) + "."

        if not message.is_from_owner:
            resp_str += f"\n\n<b>By</b>: {get_name(message.from_user)}"

        await bot.send_message(
            chat_id=extra_config.FBAN_LOG_CHANNEL, text=resp_str, disable_preview=True
        )

        await progress.edit(text=resp_str, del_in=8, block=True, disable_preview=True)

async def _perform_fban_for_aban(user_id: int, reason: str, fban_cmd_str: str) -> tuple[int, list]:
    from pyrogram import filters

    FBAN_REGEX = filters.regex(r"(New FedBan|starting a federation ban|Starting a federation ban|start a federation ban|FedBan Reason update|FedBan reason updated|Would you like to update this reason)")
    UNFBAN_REGEX = filters.regex(r"(New un-FedBan|I'll give|Un-FedBan)")

    if fban_cmd_str == "fban":
        task_filter = FBAN_REGEX
    else:
        task_filter = UNFBAN_REGEX
    
    command = f"/{fban_cmd_str} <a href='tg://user?id={user_id}'>{user_id}</a> {reason}"
    total = 0
    failed = []
    
    async for fed in FBAN_DB.find():
        total += 1
        chat_id = int(fed["_id"])
        try:
            cmd_msg = await bot.send_message(chat_id=chat_id, text=command, disable_preview=True)
            response = await cmd_msg.get_response(filters=task_filter, timeout=8)
            if not response:
                failed.append(fed["name"])
            elif "Would you like to update this reason" in response.text:
                await response.click("Update reason")
        except Exception:
            failed.append(fed["name"])
        await asyncio.sleep(0.5)
    return total, failed


async def _perform_gban_for_aban(user_id: int, reason: str, gban_cmd_str: str) -> tuple[int, list]:
    """Helper function to perform GBAN logic and return results."""
    command = f"/{gban_cmd_str} <a href='tg://user?id={user_id}'>{user_id}</a> {reason}"
    total = 0
    failed = []

    async for gban_chat in GBAN_DB.find():
        total += 1
        chat_id = int(gban_chat["_id"])
        try:
            await bot.send_message(chat_id=chat_id, text=command, disable_preview=True)
        except Exception:
            failed.append(gban_chat["name"])
        await asyncio.sleep(0.5)
    return total, failed
