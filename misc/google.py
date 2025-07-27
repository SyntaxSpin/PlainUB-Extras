import asyncio
from functools import partial
from googlesearch import search
from pyrogram.types import Message

from app import BOT, bot

ERROR_VISIBLE_DURATION = 5

def sync_search(query: str):
    """Synchronous search function to be run in a separate thread."""
    return list(search(query, num_results=5, sleep_interval=1))

@bot.add_cmd(cmd=["g", "google"])
async def google_search_handler(bot: BOT, message: Message):
    """
    CMD: G | GOOGLE
    INFO: Performs a Google search. Success messages are permanent, errors disappear.
    """
    query = message.input
    if not query:
        await message.edit("Please provide a search query.")
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await message.delete()
        return

    progress_message = await message.reply(f"Searching Google for: <code>{query}</code>...")

    try:
        # Run the synchronous search function in a thread to avoid blocking
        search_results = await asyncio.to_thread(sync_search, query)
        
        if not search_results:
            await progress_message.edit(f"No results found for <code>{query}</code>.")
            await asyncio.sleep(ERROR_VISIBLE_DURATION)
            await progress_message.delete()
            try:
                await message.delete()
            except Exception:
                pass
            return

        await progress_message.delete()
        
        output_str = f"<b>🔎 Search results for:</b> <code>{query}</code>\n\n"
        for i, link in enumerate(search_results):
            output_str += f"{i+1}. <a href='{link}'>{link}</a>\n"
            
        await bot.send_message(
            chat_id=message.chat.id,
            text=output_str,
            disable_web_page_preview=True
        )
        await message.delete()

    except Exception as e:
        error_text = f"<b>An error occurred while searching:</b>\n<code>{type(e).__name__}: {e}</code>"
        await progress_message.edit(error_text)
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await progress_message.delete()
        try:
            await message.delete()
        except Exception:
            pass
