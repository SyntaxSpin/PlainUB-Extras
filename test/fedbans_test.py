import asyncio
import html
import re

from pyrogram import filters
from pyrogram.errors import PeerIdInvalid, UserIsBlocked
from pyrogram.handlers import MessageHandler
from pyrogram.types import LinkPreviewOptions, Message, User

from app import BOT, bot

FED_BOTS_TO_QUERY = [
    609517172,  # Rose
    1376954911,  # AstrakoBot
]

def safe_escape(text: str) -> str:
    escaped_text = html.escape(str(text))
    return escaped_text.replace("&#x27;", "’")

def parse_text_response(response: Message) -> str:
    bot_name = response.from_user.first_name
    text = response.text
    lower_text = text.lower()
    not_banned_phrases = ["no bans", "not banned", "hasn't been banned"]
    if any(phrase in lower_text for phrase in not_banned_phrases):
        return f"<b>• {bot_name}:</b> Not Banned"
    else:
        return f"<b>• {bot_name}:</b> <blockquote expandable>{safe_escape(text)}</blockquote>"

async def wait_for_file(bot: BOT, chat_id: int, timeout: int = 60) -> Message | None:
    """Correctly waits for a specific file message using a temporary handler."""
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

async def query_single_bot(bot: BOT, bot_id: int, user_to_check: User) -> tuple[str, Message | None]:
    """
    Queries a single bot and returns its result text and an optional file message.
    This function is self-contained to avoid concurrency issues.
    """
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
                pass  # Ignore click errors, it likely worked anyway
            
            # Wait for the file directly here, not in a background task
            file_message = await wait_for_file(bot, bot_id)
            result_text = f"<b>• {bot_info.first_name}:</b> Bot sent a file with the full ban list."
            return result_text, file_message
        
        elif response.text:
            return parse_text_response(response), None
        
        else:
            return f"<b>• {bot_info.first_name}:</b> <i>Received an unsupported response type.</i>", None

    except (UserIsBlocked, PeerIdInvalid):
        return f"<b>• {bot_info.first_name}:</b> <i>Bot blocked or unreachable.</i>", None
    except asyncio.TimeoutError:
        return f"<b>• {bot_info.first_name}:</b> <i>No response (timeout).</i>", None
    except Exception:
        return f"<b>• {bot_info.first_name}:</b> <i>An unknown error occurred.</i>", None


@bot.add_cmd(cmd=["fstattest", "fedstattest"])
async def fed_stat_handler(bot: BOT, message: Message):
    """
    Checks a user's federation ban status using a robust concurrent method.
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

    # Create a list of tasks to run concurrently
    tasks = [query_single_bot(bot, bot_id, user_to_check) for bot_id in FED_BOTS_TO_QUERY]
    
    # Run all tasks at once and wait for them all to complete
    all_results = await asyncio.gather(*tasks)

    result_texts = []
    files_to_forward = []

    for text, file_message in all_results:
        result_texts.append(text)
        if file_message:
            files_to_forward.append(file_message)

    final_report = (
        f"<b>Federation Status for:</b> {user_to_check.mention}\n"
        f"<b>ID:</b> <code>{user_to_check.id}</code>\n\n"
        f"{'\n'.join(result_texts)}"
    )

    await progress.edit(
        final_report,
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )

    # Forward all collected files after the report is sent
    for file in files_to_forward:
        await file.forward(message.chat.id)
