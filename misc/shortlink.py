import html
import httpx
import asyncio
from pyrogram.types import Message

from app import BOT, bot

API_URL = "https://cleanuri.com/api/v1/shorten"

ERROR_VISIBLE_DURATION = 5

@bot.add_cmd(cmd=["sl", "short", "shortlink"])
async def shortlink_handler(bot: BOT, message: Message):
    """
    CMD: SL | SHORT | SHORTLINK
    INFO: Shortens a long URL. Success messages are permanent, errors disappear.
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
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await message.delete()
        return

    progress_message = await message.reply("Shortening link...")
    
    try:
        async with httpx.AsyncClient() as client:
            data_to_send = {"url": url_to_shorten}
            response = await client.post(API_URL, data=data_to_send)
            response.raise_for_status()

            data = response.json()

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
                error_message = data["error"]
                error_text = f"<b>Error from cleanuri.com:</b>\n<code>{html.escape(error_message)}</code>"
                await progress_message.edit(error_text)
            
            else:
                error_text = "<b>An unknown error occurred.</b> The API response was not as expected."
                await progress_message.edit(error_text)

    except httpx.HTTPStatusError as e:
        error_text = f"<b>HTTP Error:</b> The service returned a status code {e.response.status_code}."
        await progress_message.edit(error_text)
    except Exception as e:
        error_text = f"<b>An error occurred:</b>\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text)

    await asyncio.sleep(ERROR_VISIBLE_DURATION)
    await progress_message.delete()
    try:
        await message.delete()
    except Exception:
        pass
