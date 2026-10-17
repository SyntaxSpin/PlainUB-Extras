import asyncio
import html
from pyrogram.enums import ParseMode
from pyrogram.errors import YouBlockedUser, PeerIdInvalid, UserIsBlocked, RPCError
from app import BOT, bot, Message


async def query_sangmata(client: BOT, bot_username: str, user_id: int) -> str:
    try:
        sent_msg = await client.send_message(bot_username, str(user_id))
    except YouBlockedUser:
        return f"Exception Error: state not started or blocked."
    except (PeerIdInvalid, UserIsBlocked):
        return f"Exception Error: state not started or blocked."
    except RPCError as e:
        return f"Exception Error: {e.MESSAGE if hasattr(e, 'MESSAGE') else str(e)}"
    except Exception as e:
        return f"Exception Error: {str(e)}"

    for _ in range(15):
        await asyncio.sleep(1)
        async for msg in client.get_chat_history(bot_username, limit=3):
            if msg.id > sent_msg.id and not msg.outgoing:
                text = msg.text or msg.caption or ""
                if "No data available" in text or "No records found" in text:
                    return "Not found"
                return text

    return "Exception Error: Timed out waiting for bot response."


@bot.add_cmd(cmd=["sgb", "sang", "sangmata", "cn", "checkname"])
async def sangmata_check(bot: BOT, message: Message):
    user_id = None

    if message.replied:
        if message.replied.from_user:
            user_id = message.replied.from_user.id
        elif message.replied.sender_chat:
            user_id = message.replied.sender_chat.id
    elif message.input:
        arg = message.input.strip().split()[0]
        if arg.lstrip("-").isdigit():
            user_id = int(arg)
        else:
            try:
                user = await bot.get_users(arg)
                user_id = user.id
            except Exception as e:
                await message.reply(f"Exception Error: Could not resolve user ({e})")
                return
    else:
        await message.reply("Please provide a User ID, Username, or reply to a user.")
        return

    status_msg = await message.reply("Checking...")

    stable_res, beta_res = await asyncio.gather(
        query_sangmata(bot, "SangMata_BOT", user_id),
        query_sangmata(bot, "SangMata_beta_bot", user_id)
    )

    stable_formatted = f"<blockquote expandable>{html.escape(stable_res)}</blockquote>"
    beta_formatted = f"<blockquote expandable>{html.escape(beta_res)}</blockquote>"

    final_output = (
        f"<b>Stable :</b>\n{stable_formatted}\n\n"
        f"<b>Beta :</b>\n{beta_formatted}"
    )

    await status_msg.edit(final_output, parse_mode=ParseMode.HTML)