import asyncio

from pyrogram import filters
from pyrogram.types import Message, User
from ub_core.utils.helpers import get_name, get_user

from app import BOT, bot

FED_BOTS_TO_QUERY = [
    1087968824,  # Rose
    1788759329,  # AstrakoBot
]


def parse_fedstat_response(response: Message) -> str:
    bot_name = response.from_user.first_name
    text = response.text.html.lower()

    if "no bans" in text or "not banned in any feds" in text:
        return f"<b>• {bot_name}:</b> Not Banned"

    elif "is banned in" in text:
        reason = "No reason provided."
        if "fedban reason:" in text:
            try:
                reason_part = text.split("fedban reason:")[1].strip()
                reason = reason_part.split("<")[0].strip() or "No reason provided."
            except IndexError:
                pass
        return f"<b>• {bot_name}:</b> Banned\n  <b>Reason:</b> {reason}"

    else:
        return f"<b>• {bot_name}:</b> <i>Unrecognized response format.</i>"


@bot.add_cmd(cmd=["fstat", "fedstat"])
async def fed_stat_handler(bot: BOT, message: Message):
    """
    CMD: FSTAT / FEDSTAT
    INFO: Checks the user's federation ban status.
    USAGE:
        .fstat [user_id/username/reply]
    NOTE:
        If you don't submit the target, you've checked your own status.
    """
    progress: Message = await message.reply("Checking fedstat...")

    target_identifier = None
    if message.input:
        target_identifier = message.input
    elif message.replied:
        target_identifier = message.replied.from_user.id
    else:
        target_identifier = message.from_user.id

    try:
        user_to_check: User = await get_user(target_identifier, message)
        if isinstance(user_to_check, str):
            return await progress.edit(user_to_check)
    except Exception as e:
        return await progress.edit(f"<b>Error:</b> Could not find the specified user.\n<code>{e}</code>")
    
    results = []

    for bot_id in FED_BOTS_TO_QUERY:
        try:
            sent_cmd = await bot.send_message(
                chat_id=bot_id,
                text=f"/fedstat {user_to_check.id}"
            )
            
            response = await sent_cmd.get_response(filters=filters.user(bot_id), timeout=10)

            if response and response.text:
                results.append(parse_fedstat_response(response))
            else:
                bot_info = await bot.get_users(bot_id)
                results.append(f"<b>• {bot_info.first_name}:</b> <i>No response (timeout).</i>")

        except Exception as e:
            try:
                bot_info = await bot.get_users(bot_id)
                results.append(f"<b>• {bot_info.first_name}:</b> <i>Error during query.</i>")
            except Exception:
                results.append(f"<b>• Bot <code>{bot_id}</code>:</b> <i>Unreachable or invalid ID.</i>")
        
        await asyncio.sleep(1)

    final_report = (
        f"<b>Federation Status for:</b> {user_to_check.mention}\n"
        f"<b>ID:</b> <code>{user_to_check.id}</code>\n\n"
        f"{'\n'.join(results)}"
    )

    await progress.edit(final_report, disable_web_page_preview=True)
