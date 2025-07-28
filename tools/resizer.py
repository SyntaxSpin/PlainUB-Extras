import os
import html
import asyncio
from PIL import Image
from pyrogram.types import Message

from app import BOT, bot

TEMP_DIR = "temp_resize/"
os.makedirs(TEMP_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 8

def sync_resize_image(input_path: str, width: int, height: int) -> str:
    """
    Synchronously resizes an image to the specified dimensions.
    """
    base, ext = os.path.splitext(os.path.basename(input_path))
    output_path = os.path.join(TEMP_DIR, f"{base}_resized_{width}x{height}{ext}")
    
    with Image.open(input_path) as img:
        resized_img = img.resize((width, height), Image.Resampling.LANCZOS)
        resized_img.save(output_path)
        
    return output_path


@bot.add_cmd(cmd="resize")
async def resize_handler(bot: BOT, message: Message):
    """
    CMD: RESIZE
    INFO: Resizes an image to the specified resolution.
    USAGE: .resize [width]x[height] (reply to an image)
    """
    if not message.replied or not message.replied.photo:
        await message.edit("Please reply to an image to resize it.", del_in=ERROR_VISIBLE_DURATION)
        return

    if not message.input:
        await message.edit("Please specify the new resolution. Usage: `.resize 1920x1080`", del_in=ERROR_VISIBLE_DURATION)
        return

    try:
        width_str, height_str = message.input.lower().split('x')
        width, height = int(width_str), int(height_str)
        if not (0 < width <= 4096 and 0 < height <= 4096):
            raise ValueError("Dimensions must be between 1 and 4096.")
    except (ValueError, IndexError):
        await message.edit("Invalid resolution format. Please use `[width]x[height]`, e.g., `1920x1080`.", del_in=ERROR_VISIBLE_DURATION)
        return

    replied_msg = message.replied
    progress_message = await message.reply("<code>Downloading image...</code>")
    
    original_path = ""
    resized_path = ""
    try:
        original_path = await bot.download_media(replied_msg.photo)
        
        await progress_message.edit(f"<code>Resizing to {width}x{height}...</code>")
        
        resized_path = await asyncio.to_thread(sync_resize_image, original_path, width, height)
        
        await bot.send_document(
            chat_id=message.chat.id,
            document=resized_path,
            caption=f"Resized to: `{width}x{height}`"
        )
        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not resize image.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
        try: await message.delete()
        except: pass
    finally:
        if original_path and os.path.exists(original_path):
            os.remove(original_path)
        if resized_path and os.path.exists(resized_path):
            os.remove(resized_path)
