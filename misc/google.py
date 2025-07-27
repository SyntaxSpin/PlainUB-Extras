import asyncio
from googlesearch import search
from pyrogram.types import Message

from app import BOT, bot

ERROR_VISIBLE_DURATION = 5

@bot.add_cmd(cmd=["g", "google"])
async def google_search_handler(bot: BOT, message: Message):
    """
    CMD: G | GOOGLE
    INFO: Performs a Google search. Success messages are permanent, errors disappear.
    USAGE: .g [query]
    """
    query = message.input
    if not query:
        await message.edit("Please provide a search query. Usage: `.g What is Telegram?`")
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await message.delete()
        return

    progress_message = await message.reply(f"<i>Searching Google for:</i> <code>{query}</code>...")

    try:
        search_results = []
        for res in search(query, num_results=5, sleep_interval=1):
            search_results.append(res)

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
        for result in search_results:
            if isinstance(result, dict):
                title = result.get("title", "No Title")
                link = result.get("url", "#")
                description = result.get("description", "No description available.")
            else:
                title = getattr(result, 'title', 'No Title')
                link = getattr(result, 'url', '#')
                description = getattr(result, 'description', 'No description available.')

            output_str += f"<b><a href='{link}'>{title}</a></b>\n"
            output_str += f"└ <code>{description[:100]}...</code>\n\n"

        await bot.send_message(
            chat_id=message.chat.id,
            text=output_str,
            disable_web_page_preview=True
        )
        await message.delete()

    except Exception as e:
        error_text = f"<b>An error occurred while searching:</b>\n<code>{e}</code>"
        await progress_message.edit(error_text)
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await progress_message.delete()
        try:
            await message.delete()
        except Exception:
            pass
