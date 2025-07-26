import asyncio

from pyrogram import filters
from pyrogram.errors import PeerIdInvalid, UserIsBlocked
from pyrogram.types import Message, User

from app import BOT, bot

FED_BOTS_TO_QUERY = [
    609517172,
    1376954911,
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
    INFO: Checks a user's federation ban status.
    USAGE:
        .fstat [user_id/username/reply]
    NOTE:
        If no target is specified, it will check your own status.
    """
    progress: Message = await message.reply("Checking fedbans...")

    target_identifier = "me"
    if message.input:
        target_identifier = message.input
    elif message.replied:
        target_identifier = message.replied.from_user.id

    try:
        user_to_check: User = await bot.get_users(target_identifier)
    except Exception as e:
        return await progress.edit(f"<b>Error:</b> Could not find the specified user.\n<code>{e}</code>")
    
    results = []

    for bot_id in FED_BOTS_TO_QUERY:
        bot_info = await bot.get_users(bot_id)
        try:
            sent_cmd = await bot.send_message(
                chat_id=bot_id,
                text=f"/fedstat {user_to_check.id}"
            )
            
            response = await sent_cmd.get_response(filters=filters.user(bot_id), timeout=10)

            if response and response.text:
                results.append(parse_fedstat_response(response))
            else:
                results.append(f"<b>• {bot_info.first_name}:</b> <i>No response (timeout).</i>")

        except (UserIsBlocked, PeerIdInvalid):
            results.append(f"<b>• {bot_info.first_name}:</b> <i>Bot blocked or unreachable. Please start/unblock it manually.</i>")
        
        except Exception as e:
            results.append(f"<b>• {bot_info.first_name}:</b> <i>An unknown error occurred.</i>")
        
        await asyncio.sleep(0.5)

    final_report = (
        f"<b>Federation Status for:</b> {user_to_check.mention}\n"
        f"<b>ID:</b> <code>{user_to_check.id}</code>\n\n"
        f"{'\n'.join(results)}"
    )

    await progress.edit(final_report, disable_web_page_preview=True)
