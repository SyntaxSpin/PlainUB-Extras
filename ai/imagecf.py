# imagine.py (Cloudflare AI version)

import os
import html
import asyncio
import requests
import io
from pyrogram.types import Message, ReplyParameters
from dotenv import load_dotenv

from app import BOT, bot

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.dirname(SCRIPT_DIR)
ENV_PATH = os.path.join(MODULES_DIR, "extra_config.env")
load_dotenv(dotenv_path=ENV_PATH)

CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")

ERROR_VISIBLE_DURATION = 8

@bot.add_cmd(cmd=["image", "generate"])
async def imagine_handler(bot: BOT, message: Message):
    """
    CMD: IMAGE / GENERATE
    INFO: Generates an image from a text prompt using Cloudflare AI.
    USAGE:
        .imagine <text prompt>
    """
    if not CF_ACCOUNT_ID or not CF_API_TOKEN or "TUTAJ_WKLEJ" in CF_API_TOKEN:
        return await message.edit(
            "<b>Cloudflare AI not configured.</b>\n"
            "Please add <code>CF_ACCOUNT_ID</code> and <code>CF_API_TOKEN</code> to your <code>extra_config.env</code> file.",
            del_in=ERROR_VISIBLE_DURATION
        )

    if not message.input:
        return await message.edit("Please provide a text prompt to generate an image.", del_in=ERROR_VISIBLE_DURATION)

    prompt = message.input
    progress_message = await message.reply("<code>Generating image with Cloudflare AI... (this may take a moment)</code>")

    try:
        api_url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/@cf/stabilityai/stable-diffusion-xl-base-1.0"
        
        headers = {"Authorization": f"Bearer {CF_API_TOKEN}"}
        payload = {"prompt": prompt}
        
        response = await asyncio.to_thread(requests.post, api_url, headers=headers, json=payload)

        # Cloudflare returns the image directly as binary data, not a JSON response with a URL
        if response.ok:
            # The image data is in response.content
            image_buffer = io.BytesIO(response.content)
            image_buffer.name = "generated_by_cf.png"
            
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=image_buffer,
                caption=f"<b>Prompt:</b> <code>{html.escape(prompt)}</code>",
                reply_parameters=ReplyParameters(message_id=message.id)
            )
            await progress_message.delete()
            await message.delete()
        else:
            # If the API returns an error, show the details
            error_details = response.json()
            raise Exception(f"API Error: {error_details}")

    except Exception as e:
        error_text = f"<b>Error:</b> Could not generate image.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
