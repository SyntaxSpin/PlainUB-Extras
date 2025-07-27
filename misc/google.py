import asyncio
from functools import partial
from googlesearch import search
from pyrogram.types import Message

from app import BOT, bot

VISIBLE_DURATION = 8

def sync_search(query: str):
    """Synchronous search function to be run in a separate thread."""
    return list(search(query, num_results=5, sleep_interval=1))

@bot.add_cmd(cmd=["g", "google"])
async def google_search_handler(bot: BOT, message: Message):
    """
    CMD: G | GOOGLE
    INFO: Performs a Google search. The result is visible for a few seconds.
    """
    query = message.input
    if not query:
        await message.edit("Please provide a search query.")
        await asyncio.sleep(VISIBLE_DURATION)
        await message.delete()
        return

    progress_message = await message.reply(f"<i>Searching Google for:</i> <code>{query}</code>...")
    final_text = ""

    try:
        search_results = await asyncio.to_thread(sync_search, query)
        
        if not search_results:
            final_text = f"No results found for <code>{query}</code>."
        else:
            output_str = f"<b>🔎 Search results for:</b> <code>{query}</code>\n\n"
            for i, link in enumerate(search_results):
                output_str += f"{i+1}. <a href='{link}'>{link}</a>\n"
            final_text = output_str

    except Exception as e:
        final_text = f"<b>An error occurred while searching:</b>\n<code>{type(e).__name__}: {e}</code>"

    await progress_message.edit(final_text, disable_web_page_preview=True)
    
    await asyncio.sleep(VISIBLE_DURATION)
    await progress_message.delete()
    try:
        await message.delete()
    except Exception:
        pass
