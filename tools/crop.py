import os
import html
import asyncio
import re
from PIL import Image
from pyrogram.types import Message

from app import BOT, bot

TEMP_DIR = "temp_crop/"
os.makedirs(TEMP_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 8

def sync_crop_image(input_path: str, width: int, height: int) -> str:
    """
    Synchronously crops an image from the center to the specified dimensions.
    """
    base, ext = os.path.splitext(os.path.basename(input_path))
    output_path = os.path.join(TEMP_DIR, f"{base}_cropped{ext}")
    
    with Image.open(input_path) as img:
        orig_width, orig_height = img.size
        
        # Ensure crop dimensions are not larger than the original image
        if width > orig_width or height > orig_height:
            raise ValueError(
                f"Crop dimensions ({width}x{height}) cannot be larger than the original image ({orig_width}x{orig_height})."
            )
            
        # Calculate coordinates for a centered crop
        left = (orig_width - width) / 2
        top = (orig_height - height) / 2
        right = (orig_width + width) / 2
        bottom = (orig_height + height) / 2
        
        cropped_img = img.crop((left, top, right, bottom))
        
        # Convert to RGB if necessary to ensure compatibility
        if cropped_img.mode in ("RGBA", "P"):
            cropped_img = cropped_img.convert("RGB")
            
        cropped_img.save(output_path)
        
    return output_path


@bot.add_cmd(cmd="crop")
async def crop_handler(bot: BOT, message: Message):
    """
    CMD: CROP
    INFO: Crops the replied image from the center to specified dimensions.
    USAGE:
        .crop <width>x<height> (e.g., .crop 1280x720)
    """
    replied_msg = message.replied
    if not replied_msg or not replied_msg.photo:
        await message.edit("Please reply to an image to crop it.", del_in=ERROR_VISIBLE_DURATION)
        return

    if not message.input:
        await message.edit("Please specify the new resolution. Usage: `.crop 1280x720`", del_in=ERROR_VISIBLE_DURATION)
        return

    try:
        # Using regex for flexible separator (x or :)
        match = re.match(r"(\d+)[x:](\d+)", message.input.lower())
        if not match:
            raise ValueError("Invalid resolution format.")
        
        width, height = int(match.group(1)), int(match.group(2))
        
        if not (0 < width <= 8192 and 0 < height <= 8192):
            raise ValueError("Dimensions must be between 1 and 8192.")
    except (ValueError, IndexError):
        await message.edit("Invalid resolution format. Please use `[width]x[height]`.", del_in=ERROR_VISIBLE_DURATION)
        return

    progress_message = await message.reply("<code>Downloading photo...</code>")
    
    original_path, cropped_path = "", ""
    temp_files = []
    try:
        original_path = await bot.download_media(replied_msg)
        temp_files.append(original_path)
        
        await progress_message.edit(f"<code>Cropping to {width}x{height}...</code>")
        
        # The core logic for cropping the photo
        cropped_path = await asyncio.to_thread(sync_crop_image, original_path, width, height)
        temp_files.append(cropped_path)
        
        await progress_message.edit("<code>Sending photo...</code>")
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=cropped_path,
            caption=f"Cropped to: `{width}x{height}`",
            reply_to_message_id=replied_msg.id
        )
        
        # Final cleanup
        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not crop media.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
        try: await message.delete()
        except: pass
    finally:
        for f in temp_files:
            if f and os.path.exists(f):
                os.remove(f)
