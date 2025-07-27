from googlesearch import search
from pyrogram.types import Message

from app import BOT, bot

@bot.add_cmd(cmd=["g", "google"])
async def google_search_handler(bot: BOT, message: Message):
    """
    CMD: G | GOOGLE
    INFO: Performs a Google search and returns the top 5 results.
    USAGE: .g [query]
    """
    query = message.input
    if not query:
        await message.edit("Please provide a search query. Usage: `.g What is Telegram?`")
        return

    await message.edit(f"Searching Google for: <code>{query}</code>...")

    try:
        # Perform the search, limit to 5 results
        search_results = list(search(query, num_results=5))

        if not search_results:
            await message.edit(f"No results found for <code>{query}</code>.")
            return

        # Format the results
        output_str = f"<b>🔎 Search results for:</b> <code>{query}</code>\n\n"
        for i, result in enumerate(search_results):
            # The library sometimes returns dicts, sometimes objects. This handles both.
            if isinstance(result, dict):
                title = result.get("title", "No Title")
                link = result.get("url", "#")
                description = result.get("description", "No description available.")
            else: # Fallback for older versions or different response types
                title = getattr(result, 'title', 'No Title')
                link = getattr(result, 'url', '#')
                description = getattr(result, 'description', 'No description available.')

            output_str += f"<b><a href='{link}'>{title}</a></b>\n"
            output_str += f"└ <code>{description}</code>\n\n"

        await message.edit(
            output_str,
            disable_web_page_preview=True
        )

    except Exception as e:
        await message.edit(f"<b>An error occurred while searching:</b>\n<code>{e}</code>")
