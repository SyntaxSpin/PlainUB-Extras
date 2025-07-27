import html
import httpx
from pyrogram.types import Message

from app import BOT, bot

API_URL = "https://cleanuri.com/api/v1/shorten"

@bot.add_cmd(cmd=["sl", "short", "shortlink"])
async def shortlink_handler(bot: BOT, message: Message):
    """
    CMD: SL | SHORT | SHORTLINK
    INFO: Shortens a long URL using the cleanuri.com service.
    USAGE: .sl [url] or reply to a message containing a URL.
    """
    
    url_to_shorten = ""

    if message.input:
        url_to_shorten = message.input
    elif message.replied:
        if message.replied.text:
            url_to_shorten = message.replied.text
        elif message.replied.caption:
            url_to_shorten = message.replied.caption
    
    if not url_to_shorten:
        await message.edit("Please provide a URL to shorten or reply to a message containing one.")
        return

    await message.edit("Shortening link...")
    
    try:
        async with httpx.AsyncClient() as client:
            data_to_send = {"url": url_to_shorten}
            response = await client.post(API_URL, data=data_to_send)
            response.raise_for_status()

            data = response.json()
            
            if "result_url" in data:
                shortened_url = data["result_url"]
                final_text = (
                    f"<b>Original URL:</b> <code>{html.escape(url_to_shorten)}</code>\n"
                    f"<b>Shortened URL:</b> <code>{shortened_url}</code>"
                )
                await message.edit(final_text, disable_web_page_preview=True)
            elif "error" in data:
                error_message = data["error"]
                await message.edit(
                    f"<b>Error from cleanuri.com:</b>\n<code>{html.escape(error_message)}</code>"
                )
            else:
                await message.edit("<b>An unknown error occurred.</b> The API response was not as expected.")

    except httpx.HTTPStatusError as e:
        await message.edit(
            f"<b>HTTP Error:</b> The service returned a status code {e.response.status_code}."
        )
    except Exception as e:
        await message.edit(f"<b>An error occurred:</b>\n<code>{html.escape(str(e))}</code>")
