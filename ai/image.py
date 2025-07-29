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

MODELSLAB_API_KEY = os.getenv("MODELSLAB_API_KEY")

ERROR_VISIBLE_DURATION = 15

@bot.add_cmd(cmd=["imagine", "gen"])
async def imagine_handler(bot: BOT, message: Message):
    """
    CMD: IMAGINE / DALLE
    INFO: Generates an image from a text prompt using ModelsLab API.
    USAGE:
        .imagine <text prompt>
    """
    if not MODELSLAB_API_KEY or MODELSLAB_API_KEY == "YOUR_KEY":
        return await message.edit(
            "<b>ModelsLab API Key not configured.</b>\n"
            "Please add <code>MODELSLAB_API_KEY</code> to your <code>extra_config.env</code> file.",
            del_in=ERROR_VISIBLE_DURATION
        )

    if not message.input:
        return await message.edit("Please provide a text prompt to generate an image.", del_in=ERROR_VISIBLE_DURATION)

    prompt = message.input
    progress_message = await message.reply("<code>Generating image...</code>")

    try:
        api_url = "https://modelslab.com/api/v6/images/text2img"
        
        payload = {
            "key": MODELSLAB_API_KEY,
            "model_id": "flux",
            "prompt": prompt,
            "negative_prompt": "ugly, disfigured, low quality, blurry, nsfw, text, watermark",
            "width": "512",
            "height": "512",
            "samples": "1",
            "num_inference_steps": "20",
            "safety_checker": "yes",
            "enhance_prompt": "yes",
            "seed": None,
            "guidance_scale": 7.5
        }
        
        response = await asyncio.to_thread(requests.post, api_url, json=payload)
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
            # Show the full API response for debugging if something goes wrong
            raise Exception(f"API returned non-success status: {response_data}")

    except Exception as e:
        error_text = f"<b>Error:</b> Could not generate image.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
