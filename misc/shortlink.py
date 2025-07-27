import html
import requests
import asyncio
from pyrogram.types import Message

from app import BOT, bot

API_URL = "https://cleanuri.com/api/v1/shorten"
ERROR_VISIBLE_DURATION = 5

def sync_shorten(url: str):
    """Synchronous shorten function to be run in a separate thread."""
    response = requests.post(API_URL, data={"url": url})
    response.raise_for_status()
    return response.json()

@bot.add_cmd(cmd=["sl", "short", "shortlink"])
async def shortlink_handler(bot: BOT, message: Message):
    """
    CMD: SL | SHORT | SHORTLINK
    INFO: Shortens a long URL. Success messages are permanent, errors disappear.
    """
    url_to_shorten = ""

    if message.input:
        url_to_shorten = message.input
    elif message.replied:
        url_to_shorten = message.replied.text or message.replied.caption
    
    if not url_to_shorten:
        await message.edit("Please provide a URL.")
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await message.delete()
        return

    progress_message = await message.reply("Shortening link...")
    
    try:
        data = await asyncio.to_thread(sync_shorten, url_to_shorten)
        
        if "result_url" in data:
            await progress_message.delete()
            shortened_url = data["result_url"]
            final_text = (
                f"<b>Original URL:</b> <code>{html.escape(url_to_shorten)}</code>\n"
                f"<b>Shortened URL:</b> <code>{shortened_url}</code>"
            )
            await bot.send_message(
                chat_id=message.chat.id,
                text=final_text,
                disable_web_page_preview=True
            )
            await message.delete()
            return

        elif "error" in data:
            error_text = f"<b>API Error:</b>\n<code>{html.escape(data['error'])}</code>"
            await progress_message.edit(error_text)
        
        else:
            await progress_message.edit("<b>An unknown API error occurred.</b>")

    except Exception as e:
        error_text = f"<b>An error occurred:</b>\n<code>{type(e).__name__}: {e}</code>"
        await progress_message.edit(error_text)

    await asyncio.sleep(ERROR_VISIBLE_DURATION)
    await progress_message.delete()
    try:
        await message.delete()
    except Exception:
        pass
