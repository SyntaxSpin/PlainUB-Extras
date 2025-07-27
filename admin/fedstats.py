import asyncio
import html
import os

from pyrogram import filters
from pyrogram.errors import PeerIdInvalid, UserIsBlocked
from pyrogram.types import Message, User

from app import BOT, bot

FED_BOTS_TO_QUERY = [
    609517172,  # Rose
    1376954911,  # AstrakoBot
]

def safe_escape(text: str) -> str:
    escaped_text = html.escape(str(text))
    return escaped_text.replace("&#x27;", "’")

def parse_text_response(response: Message) -> str:
    """Parses a non-file text response from a fed bot using safe_escape."""
    bot_name = response.from_user.first_name
    text = response.text
    lower_text = text.lower()

    not_banned_phrases = ["no bans", "not banned", "hasn't been banned"]

    if any(phrase in lower_text for phrase in not_banned_phrases):
        return f"<b>• {bot_name}:</b> Not Banned"
    else:
        return f"<b>• {bot_name}:</b> <blockquote expandable>{safe_escape(text)}</blockquote>"


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
    progress: Message = await message.reply("Checking fedstat...")

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
            sent_cmd = await bot.send_message(chat_id=bot_id, text=f"/fedstat {user_to_check.id}")
            response = await sent_cmd.get_response(filters=filters.user(bot_id), timeout=15)

            if not response:
                results.append(f"<b>• {bot_info.first_name}:</b> <i>No response (timeout).</i>")
                continue
            
            if response.text and "checking" in response.text.lower():
                await asyncio.sleep(3)
                response = await bot.get_messages(bot_id, response.id)

            if response.reply_markup and "Make the fedban file" in str(response.reply_markup):
                await response.click(0)
                await asyncio.sleep(5)
                response = await bot.get_messages(bot_id, response.id)

            if response.document:
                file_path = None
                try:
                    file_path = await bot.download_media(response.document)
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    
                    if len(content) > 3800:
                        await response.forward(message.chat.id)
                        results.append(f"<b>• {bot_info.first_name}:</b> Banned (details in forwarded file - too long)")
                    else:
                        results.append(f"<b>• {bot_info.first_name}:</b> <blockquote expandable>{safe_escape(content)}</blockquote>")
                
                finally:
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)

            elif response.text:
                results.append(parse_text_response(response))
            
            else:
                results.append(f"<b>• {bot_info.first_name}:</b> <i>Received an unsupported response type.</i>")

        except (UserIsBlocked, PeerIdInvalid):
            results.append(f"<b>• {bot_info.first_name}:</b> <i>Bot blocked or unreachable. Please start/unblock it manually.</i>")
        except asyncio.TimeoutError:
            results.append(f"<b>• {bot_info.first_name}:</b> <i>No response (timeout).</i>")
        except Exception:
            results.append(f"<b>• {bot_info.first_name}:</b> <i>An unknown error occurred.</i>")

        await asyncio.sleep(0.5)

    final_report = (
        f"<b>Federation Status for:</b> {user_to_check.mention}\n"
        f"<b>ID:</b> <code>{user_to_check.id}</code>\n\n"
        f"{'\n'.join(results)}"
    )

    await progress.edit(final_report, disable_web_page_preview=True)
