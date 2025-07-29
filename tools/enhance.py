import os
import html
import asyncio
from PIL import Image, ImageEnhance, ImageFilter
from pyrogram.types import ReplyParameters

from app import BOT, Message, bot

TEMP_DIR = "temp_enhance/"
os.makedirs(TEMP_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 8

def sync_enhance_image(input_path: str) -> tuple[str, int, int]:
    """
    Synchronously upscales, enhances, and smooths an image.
    Returns the output path, new width, and new height.
    """
    base, ext = os.path.splitext(os.path.basename(input_path))
    output_path = os.path.join(TEMP_DIR, f"{base}_enhanced.png") # Force PNG for quality
    
    with Image.open(input_path) as img:
        # Convert to a mode that supports enhancements well
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")

        # Step 1: Upscale the image 2x for more detail to work with
        orig_width, orig_height = img.size
        new_width = orig_width * 2
        new_height = orig_height * 2
        
        upscaled_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Step 2: Sharpen the image to make details crisper
        enhancer_sharp = ImageEnhance.Sharpness(upscaled_img)
        sharpened_img = enhancer_sharp.enhance(2.0)
        
        # Step 3: Smooth the image to reduce sharpness artifacts
        smoothed_img = sharpened_img.filter(ImageFilter.SMOOTH)
        
        # Step 4: Slightly increase contrast to make the image "pop"
        enhancer_contrast = ImageEnhance.Contrast(smoothed_img)
        final_image = enhancer_contrast.enhance(1.2)
            
        final_image.save(output_path, "PNG")
        
    return output_path, new_width, new_height


@bot.add_cmd(cmd="enhance")
async def enhance_handler(bot: BOT, message: Message):
    """
    CMD: ENHANCE
    INFO: Upscales and enhances the quality of the replied image.
    USAGE:
        .enhance
    """
    replied_msg = message.replied
    is_photo = replied_msg and (replied_msg.photo or (replied_msg.document and replied_msg.document.mime_type.startswith("image/")))
    if not is_photo:
        await message.edit("Please reply to an image to use this command.", del_in=ERROR_VISIBLE_DURATION)
        return
        
    progress_message = await message.reply("<code>Downloading photo...</code>")
    
    original_path, enhanced_path = "", ""
    temp_files = []
    try:
        original_path = await bot.download_media(replied_msg)
        temp_files.append(original_path)
        
        await progress_message.edit("<code>Enhancing quality...</code>")
        
        # The core logic for enhancing the photo
        enhanced_path, new_width, new_height = await asyncio.to_thread(sync_enhance_image, original_path)
        temp_files.append(enhanced_path)
        
        await progress_message.edit("<code>Sending photo as file...</code>")
        
        # Send the enhanced image as a document using the correct method
        await bot.send_document(
            chat_id=message.chat.id,
            document=enhanced_path,
            caption=f"Enhanced to: `{new_width}x{new_height}`",
            reply_parameters=ReplyParameters(message_id=replied_msg.id)
        )
        
        # Final cleanup
        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not enhance media.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
        try: await message.delete()
        except: pass
    finally:
        for f in temp_files:
            if f and os.path.exists(f):
                os.remove(f)
