import os
import html
import asyncio
import requests
import time
import base64
from urllib.parse import urlencode
from pyrogram.types import Message

from app import BOT, bot

TEMP_DIR = "temp_screenshots/"
os.makedirs(TEMP_DIR, exist_ok=True)


@bot.add_cmd(cmd=["screenshot", "ss"])
async def screenshot_handler(bot: BOT, message: Message):
    if not message.input:
        return await message.reply("<b>Usage:</b> <code>.screenshot [url]</code>")

    url = message.input.strip()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    progress_msg = await message.reply(f"<code>Taking screenshot...</code>")
    
    output_path = os.path.join(TEMP_DIR, f"screenshot_{int(time.time())}.jpeg")

    try:
        api_endpoint = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?screenshot=true&strategy=desktop&url={url}"

        def do_request():
            return requests.get(api_endpoint, timeout=60)

        response = await asyncio.to_thread(do_request)
        response.raise_for_status()

        result = response.json()
        
        screenshot_data = result.get("lighthouseResult", {}).get("audits", {}).get("final-screenshot", {}).get("details", {}).get("data")
        
        if not screenshot_data:
            raise ValueError("Google API did not return a screenshot. The site may be inaccessible or too slow.")

        image_data = base64.b64decode(screenshot_data.replace("data:image/jpeg;base64,", ""))

        with open(output_path, "wb") as f:
            f.write(image_data)
        
        if os.path.exists(output_path):
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=output_path,
                caption=f"Screenshot of: <code>{html.escape(url)}</code>",
                reply_to_message_id=message.id
            )
            await progress_msg.delete()
            await message.delete()
        else:
            raise FileNotFoundError("Screenshot file was not created.")

    except Exception as e:
        await progress_msg.edit(f"<b>Error:</b> <code>{html.escape(str(e))}</code>", del_in=8)
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)
