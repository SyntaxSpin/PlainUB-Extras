import html
import wikipediaapi
import asyncio
from pyrogram.types import LinkPreviewOptions, Message

from app import BOT, bot

ERROR_VISIBLE_DURATION = 8

HEADERS = {"User-Agent": "CoolCatBot/1.0 (https://github.com/telegram)"}
WIKI_OBJS = {
    "en": wikipediaapi.Wikipedia("en", headers=HEADERS),
    "pl": wikipediaapi.Wikipedia("pl", headers=HEADERS),
    "de": wikipediaapi.Wikipedia("de", headers=HEADERS),
    "es": wikipediaapi.Wikipedia("es", headers=HEADERS),
    "fr": wikipediaapi.Wikipedia("fr", headers=HEADERS),
}

def sync_wiki_search(lang: str, query: str) -> tuple[str, str, str] | None:
    """
    Synchronous function to search Wikipedia.
    Returns a tuple of (title, summary, url) or None if not found.
    """
    if lang not in WIKI_OBJS:
        wiki = wikipediaapi.Wikipedia(lang, headers=HEADERS)
    else:
        wiki = WIKI_OBJS[lang]

    page = wiki.page(query)
    if page.exists():
        summary = page.summary[:300]
        if len(page.summary) > 300:
            summary = summary.rsplit(' ', 1)[0] + "..."
            
        return page.title, summary, page.fullurl
    return None

@bot.add_cmd(cmd=["wiki", "wikipedia"])
async def wiki_handler(bot: BOT, message: Message):
    """
    CMD: WIKI | WIKIPEDIA
    INFO: Searches for a page on Wikipedia.
    USAGE: .wiki [lang] [query] or .wiki [query] (defaults to English)
    """
    
    parts = message.input.split(maxsplit=1) if message.input else []
    lang = "en"
    query = ""

    if len(parts) == 2 and len(parts[0]) == 2:
        lang = parts[0].lower()
        query = parts[1]
    elif len(parts) >= 1:
        query = message.input
    else:
        await message.edit("Please provide a search query. Usage: `.wiki [lang] <query>`")
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await message.delete()
        return

    progress_message = await message.reply(f"Searching Wikipedia ({lang}) for: <code>{html.escape(query)}</code>...")

    try:
        result = await asyncio.to_thread(sync_wiki_search, lang, query)
        
        if result:
            title, summary, url = result
            
            final_text = (
                f"<b>📖 <a href='{url}'>{html.escape(title)}</a></b>\n\n"
                f"{html.escape(summary)}"
            )
            
            await progress_message.edit(
                final_text,
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
            await message.delete()

        else:
            error_text = f"Could not find any Wikipedia page for <code>{html.escape(query)}</code> in {lang}."
            await progress_message.edit(error_text)
            await asyncio.sleep(ERROR_VISIBLE_DURATION)
            await progress_message.delete()
            await message.delete()

    except Exception as e:
        error_text = f"<b>An error occurred:</b>\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text)
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await progress_message.delete()
        try:
            await message.delete()
        except Exception:
            pass
