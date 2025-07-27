import asyncio
import html
import re

from pyrogram.handlers import MessageHandler
from pyrogram import filters
from pyrogram.errors import PeerIdInvalid, UserIsBlocked
from pyrogram.types import LinkPreviewOptions, Message, User

from app import BOT, bot

FED_BOTS_TO_QUERY = [
    609517172,  # Rose
    1376954911,  # AstrakoBot
]

def safe_escape(text: str) -> str:
    """Escapes HTML characters and fixes apostrophe encoding for Telegram."""
    escaped_text = html.escape(str(text))
    return escaped_text.replace("&#x27;", "’")

def parse_text_response(response: Message) -> str:
    """Parses a non-file text response and formats it correctly."""
    bot_name = response.from_user.first_name
    text = response.text
    lower_text = text.lower()
    not_banned_phrases = ["no bans", "not banned", "hasn't been banned"]
    if any(phrase in lower_text for phrase in not_banned_phrases):
        return f"<b>• {bot_name}:</b> Not Banned"
    else:
        return f"<b>• {bot_name}:</b> <blockquote expandable>{safe_escape(text)}</blockquote>"

async def wait_for_rose_file(bot: BOT, chat_id: int, timeout: int = 60) -> Message | None:
    """
    This is the dedicated file listener. It waits patiently in the background.
    It waits for 60 seconds and returns the file message, or None on timeout.
    """
    required_filters = (
        filters.user(chat_id) & 
        filters.document & 
        filters.regex(r"List of fedbans", flags=re.IGNORECASE)
    )
    
    queue = asyncio.Queue()

    async def _handler(_, message: Message):
        await queue.put(message)

    handler = bot.add_handler(MessageHandler(_handler, filters=required_filters), group=-1)

    try:
        return await asyncio.wait_for(queue.get(), timeout=timeout)
    except asyncio.TimeoutError:
        return None
    finally:
        bot.remove_handler(*handler)

@bot.add_cmd(cmd=["fstattest", "fedstattest"])
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
    file_listener_task = None

    for bot_id in FED_BOTS_TO_QUERY:
        bot_info = await bot.get_users(bot_id)
        try:
            sent_cmd = await bot.send_message(chat_id=bot_id, text=f"/fedstat {user_to_check.id}")
            response = await sent_cmd.get_response(filters=filters.user(bot_id), timeout=20)

            if response.text and "checking" in response.text.lower():
                response = await sent_cmd.get_response(filters=filters.user(bot_id), timeout=20)

            if response.reply_markup and "Make the fedban file" in str(response.reply_markup):
                try:
                    await response.click(0)
                except Exception:
                    pass
                
                file_listener_task = asyncio.create_task(wait_for_rose_file(bot, bot_id))
                results.append(f"<b>• {bot_info.first_name}:</b> Bot is preparing a file. It will be sent shortly.")
            
            elif response.text:
                results.append(parse_text_response(response))
            
            else:
                results.append(f"<b>• {bot_info.first_name}:</b> <i>Received an unsupported response type.</i>")

        except (UserIsBlocked, PeerIdInvalid):
            results.append(f"<b>• {bot_info.first_name}:</b> <i>Bot blocked or unreachable.</i>")
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

    await progress.edit(
        final_report,
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )

    if file_listener_task:
        file_message = await file_listener_task
        if file_message:
            await file_message.forward(message.chat.id)
