import os
import html
import asyncio
import requests
import time
from urllib.parse import urlparse
from pyrogram.types import Message
from dotenv import load_dotenv

from app import BOT, bot

API_URL = "https://shot.screenshotapi.net/screenshot"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.dirname(SCRIPT_DIR)
ENV_PATH = os.path.join(MODULES_DIR, "extra_config.env")
load_dotenv(dotenv_path=ENV_PATH)
SCREENSHOT_API_KEY = os.getenv("SCREENSHOT_API_KEY")
TEMP_DIR = "temp_screenshots/"
os.makedirs(TEMP_DIR, exist_ok=True)


@bot.add_cmd(cmd=["screenshot", "ss"])
async def screenshot_handler(bot: BOT, message: Message):
    """
    CMD: SCREENSHOT / SS
    INFO: Takes a screenshot of a given webpage.
    USAGE:
        .screenshot [url]
    """

    if not SCREENSHOT_API_KEY or "YOUR_KEY" in SCREENSHOT_API_KEY:
        return await message.reply("<b>SCREENSHOT_API_KEY from is not configured.</b>", del_in=ERROR_VISIBLE_DURATION)
    if not message.input:
        return await message.reply("<b>Usage:</b> .screenshot [url]", del_in=ERROR_VISIBLE_DURATION)

    url = message.input.strip()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    progress_msg = await message.reply(f"<code>Taking screenshot...</code>")

    params = {
        "token": SCREENSHOT_API_KEY,
        "url": url,
        "full_page": "true",
        "fresh": "true",
        "output": "image",
        "file_type": "png",
        "wait_for_event": "load"
    }
    
    output_path = os.path.join(TEMP_DIR, f"screenshot_{int(time.time())}.png")

    try:
        def do_request():
            return requests.get(API_URL, params=params, stream=True, timeout=120)

        response = await asyncio.to_thread(do_request)

        if response.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=output_path,
                caption=f"Screenshot of: <code>{html.escape(url)}</code>",
                reply_to_message_id=message.id
            )
            await progress_msg.delete()
            await message.delete()
        else:
            try:
                error_data = response.json()
                error_message = error_data.get("error", "Unknown API error")
            except requests.exceptions.JSONDecodeError:
                error_message = response.text
            
            await progress_msg.edit(f"<b>API Error:</b> <code>{html.escape(error_message)}</code>", del_in=10)

    except Exception as e:
        await progress_msg.edit(f"<b>Error:</b> <code>{html.escape(str(e))}</code>", del_in=10)
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)
