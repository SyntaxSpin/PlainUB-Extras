import os
import html
import asyncio
import requests
import io
from pyrogram.types import Message, ReplyParameters
from dotenv import load_dotenv
from PIL import Image

from app import BOT, bot

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.dirname(SCRIPT_DIR)
ENV_PATH = os.path.join(MODULES_DIR, "extra_config.env")
load_dotenv(dotenv_path=ENV_PATH)

MODELSLAB_API_KEY = os.getenv("MODELSLAB_API_KEY")

UBOT_DIR = os.path.dirname(os.path.dirname(MODULES_DIR)) 
LOGO_PATH = os.path.join(UBOT_DIR, "assets", "light.png")

TEMP_DIR = "temp_imagine/"
os.makedirs(TEMP_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 8

def sync_add_watermark(image_url: str) -> io.BytesIO:
    response = requests.get(image_url, stream=True)
    response.raise_for_status()
    
    main_image = Image.open(response.raw).convert("RGBA")
    
    if not os.path.exists(LOGO_PATH):
        bio = io.BytesIO()
        main_image.save(bio, "PNG")
        bio.seek(0)
        return bio
        
    logo = Image.open(LOGO_PATH).convert("RGBA")
    
    main_width, main_height = main_image.size
    logo_width = main_width // 5
    logo_ratio = logo.height / logo.width
    new_logo_height = int(logo_width * logo_ratio)
    
    resized_logo = logo.resize((logo_width, new_logo_height), Image.Resampling.LANCZOS)
    
    padding = 20
    position = (main_width - resized_logo.width - padding, main_height - resized_logo.height - padding)
    
    main_image.paste(resized_logo, position, resized_logo)
    
    final_buffer = io.BytesIO()
    final_buffer.name = "generated_with_logo.png"
    main_image.save(final_buffer, "PNG")
    final_buffer.seek(0)
    
    return final_buffer

@bot.add_cmd(cmd=["imagine", "dalle"])
async def imagine_handler(bot: BOT, message: Message):
    """
    CMD: IMAGINE / DALLE
    INFO: Generates an image from a text prompt and adds a watermark.
    USAGE:
        .imagine <text prompt>
    """
    if not MODELSLAB_API_KEY or MODELSLAB_API_KEY == "TUTAJ_WKLEJ_SWOJ_NOWY_KLUCZ_API":
        return await message.edit("<b>ModelsLab API Key not configured.</b>", del_in=ERROR_VISIBLE_DURATION)

    if not message.input:
        return await message.edit("Please provide a text prompt.", del_in=ERROR_VISIBLE_DURATION)

    prompt = message.input
    progress_message = await message.reply("<code>Generating image... (this may take 20-40 seconds)</code>")

    try:
        api_url = "https://modelslab.com/api/v6/images/text2img"
        payload = {
            "key": MODELSLAB_API_KEY, "model_id": "epicrealism_natural-sin-rc1-vae", 
            "prompt": prompt, "negative_prompt": "ugly, disfigured, low quality, blurry, nsfw",
            "width": "512", "height": "512", "samples": "1", "num_inference_steps": "20",
            "safety_checker": "yes", "enhance_prompt": "yes", "seed": None, "guidance_scale": 7.5
        }
        
        response = await asyncio.to_thread(requests.post, api_url, json=payload)
        response_data = response.json()

        if response_data.get("status") == "success":
            image_url = response_data["output"][0]
            
            final_image_buffer = await asyncio.to_thread(sync_add_watermark, image_url)
            
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=final_image_buffer,
                caption=f"<b>Prompt:</b> <code>{html.escape(prompt)}</code>",
                reply_parameters=ReplyParameters(message_id=message.id)
            )
            await progress_message.delete()
            await message.delete()
        else:
            error_msg = response_data.get("message") or response_data.get("messege", "Unknown API error.")
            raise Exception(f"API Error: {error_msg}")

    except Exception as e:
        error_text = f"<b>Error:</b> Could not generate image.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
