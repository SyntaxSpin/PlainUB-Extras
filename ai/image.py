import os
import html
import asyncio
import requests
from pyrogram.types import Message, ReplyParameters
from dotenv import load_dotenv

from app import BOT, bot

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.dirname(SCRIPT_DIR)
ENV_PATH = os.path.join(MODULES_DIR, "extra_config.env")
load_dotenv(dotenv_path=ENV_PATH)

STABLE_DIFFUSION_API_KEY = os.getenv("STABLE_DIFFUSION_API_KEY")

ERROR_VISIBLE_DURATION = 8

@bot.add_cmd(cmd=["imagine", "dalle"])
async def imagine_handler(bot: BOT, message: Message):
    """
    CMD: IMAGINE / DALLE
    INFO: Generates an image from a text prompt using Stable Diffusion.
    USAGE:
        .imagine <text prompt>
    """
    if not STABLE_DIFFUSION_API_KEY or STABLE_DIFFUSION_API_KEY == "TUTAJ_WKLEJ_SWOJ_KLUCZ_API":
        return await message.edit(
            "<b>Stable Diffusion API Key not configured.</b>\n"
            "Please add it to your <code>extra_config.env</code> file.",
            del_in=ERROR_VISIBLE_DURATION
        )

    if not message.input:
        return await message.edit("Please provide a text prompt to generate an image.", del_in=ERROR_VISIBLE_DURATION)

    prompt = message.input
    progress_message = await message.reply("<code>Generating image...</code>")

    try:
        api_url = "https://stablediffusionapi.com/api/v3/text2img"
        payload = {
            "key": STABLE_DIFFUSION_API_KEY,
            "prompt": prompt,
            "negative_prompt": "bad anatomy, blurry, low quality",
            "width": "512",
            "height": "512",
            "samples": "1",
            "num_inference_steps": "20",
            "seed": None,
            "guidance_scale": 7.5,
            "webhook": None,
            "track_id": None,
        }
        
        response = await asyncio.to_thread(requests.post, api_url, json=payload)
        response.raise_for_status()
        response_data = response.json()

        if response_data.get("status") == "success":
            image_url = response_data["output"][0]
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=image_url,
                caption=f"<b>Prompt:</b> <code>{html.escape(prompt)}</code>",
                reply_parameters=ReplyParameters(message_id=message.id)
            )
            await progress_message.delete()
            await message.delete()
        else:
            error_msg = response_data.get("message", "Unknown API error.")
            raise Exception(f"API Error: {error_msg}")

    except Exception as e:
        error_text = (
            f"<b>Error:</b> Could not generate image.\n"
            f"<b>Type:</b> <code>{type(e).__name__}</code>\n"
            f"<b>Details:</b> <code>{html.escape(str(e))}</code>"
        )
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
