import os
import html
import asyncio
from PIL import Image
from pyrogram.types import Message

from app import BOT, bot

TEMP_DIR = "temp_upscale/"
os.makedirs(TEMP_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 8

def sync_upscale_image(input_path: str, scale_factor: int = 2) -> tuple[str, int, int]:
    """
    Synchronously upscales an image by a given factor.
    Returns the output path, new width, and new height.
    """
    base, ext = os.path.splitext(os.path.basename(input_path))
    output_path = os.path.join(TEMP_DIR, f"{base}_upscaled{ext}")
    
    with Image.open(input_path) as img:
        orig_width, orig_height = img.size
        new_width = orig_width * scale_factor
        new_height = orig_height * scale_factor
        
        upscaled_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary to ensure compatibility
        if upscaled_img.mode in ("RGBA", "P"):
            upscaled_img = upscaled_img.convert("RGB")
            
        upscaled_img.save(output_path)
        
    return output_path, new_width, new_height


@bot.add_cmd(cmd="upscale")
async def upscale_handler(bot: BOT, message: Message):
    """
    CMD: UPSCALE
    INFO: Upscales the replied image to 2x its original size.
    USAGE:
        .upscale
    """
    replied_msg = message.replied
    is_photo = replied_msg and (replied_msg.photo or (replied_msg.document and replied_msg.document.mime_type.startswith("image/")))
    if not is_photo:
        await message.edit("Please reply to an image to use this command.", del_in=ERROR_VISIBLE_DURATION)
        return
    
    progress_message = await message.reply("<code>Downloading photo...</code>")
    
    original_path, upscaled_path = "", ""
    temp_files = []
    try:
        original_path = await bot.download_media(replied_msg)
        temp_files.append(original_path)
        
        await progress_message.edit("<code>Upscaling...</code>")
        
        # The core logic for upscaling the photo
        upscaled_path, new_width, new_height = await asyncio.to_thread(sync_upscale_image, original_path)
        temp_files.append(upscaled_path)
        
        await progress_message.edit("<code>Sending photo...</code>")
        
        # Send as a photo instead of a document
        await bot.send_photo(
            message.chat.id,
            photo=upscaled_path,
            caption=f"Upscaled to: `{new_width}x{new_height}`",
            reply_to_message_id=replied_msg.id
        )
        
        # Final cleanup
        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not upscale media.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
        try: await message.delete()
        except: pass
    finally:
        for f in temp_files:
            if f and os.path.exists(f):
                os.remove(f)
