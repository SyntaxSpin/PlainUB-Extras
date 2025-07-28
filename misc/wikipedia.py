import html
import wikipediaapi
import asyncio
import re
from pyrogram.types import LinkPreviewOptions, Message

from app import BOT, bot

ERROR_VISIBLE_DURATION = 8
DEFAULT_WIKI_LANG = "en"

HEADERS = {"User-Agent": "MyCoolUserBot/1.0 (https://github.com/telegram)"}
WIKI_OBJS = {
    "en": wikipediaapi.Wikipedia("en", headers=HEADERS),
    "pl": wikipediaapi.Wikipedia("pl", headers=HEADERS),
    "de": wikipediaapi.Wikipedia("de", headers=HEADERS),
    "es": wikipediaapi.Wikipedia("es", headers=HEADERS),
    "fr": wikipediaapi.Wikipedia("fr", headers=HEADERS),
    "ru": wikipediaapi.Wikipedia("ru", headers=HEADERS),
    "it": wikipediaapi.Wikipedia("it", headers=HEADERS),
    "ja": wikipediaapi.Wikipedia("ja", headers=HEADERS),
    "pt": wikipediaapi.Wikipedia("pt", headers=HEADERS),
    "zh": wikipediaapi.Wikipedia("zh", headers=HEADERS),
    "uk": wikipediaapi.Wikipedia("uk", headers=HEADERS),
}

def sync_wiki_search(lang: str, query: str) -> tuple[str, str, str] | None:
    """Synchronous function to search Wikipedia."""
    wiki = WIKI_OBJS.get(lang)
    if not wiki:
        wiki = wikipediaapi.Wikipedia(lang, headers=HEADERS)
        WIKI_OBJS[lang] = wiki

    page = wiki.page(query)
    if page.exists():
        summary = page.summary[:350]
        if len(page.summary) > 350:
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
    
    if not message.input:
        await message.edit("Please provide a search query.")
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await message.delete()
        return

    lang = DEFAULT_WIKI_LANG
    query = message.input
    
    match = re.match(r"^([a-z]{2})\s+(.+)", message.input, re.IGNORECASE | re.DOTALL)
    
    if match:
        lang = match.group(1).lower()
        query = match.group(2)

    progress_message = await message.reply(f"Searching Wikipedia ({lang}) for: <code>{html.escape(query)}</code>...")

    try:
        result = await asyncio.to_thread(sync_wiki_search, lang, query)
        
        if result:
            title, summary, url = result
            final_text = (
                f"<b>📖 <a href='{url}'>{html.escape(title)}</a></b>\n\n"
                f"{html.escape(summary)}"
            )
            await progress_message.edit(final_text, link_preview_options=LinkPreviewOptions(is_disabled=True))
            await message.delete()
        else:
            error_text = f"Could not find any Wikipedia page for <code>{html.escape(query)}</code> in '{lang}'."
            await progress_message.edit(error_text)
            await asyncio.sleep(ERROR_VISIBLE_DURATION)
            await message.delete()
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
