import os
import html
import asyncio
from PIL import Image
from pyrogram.types import Message

from app import BOT, bot

TEMP_DIR = "temp_resize/"
os.makedirs(TEMP_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 8

async def run_command(command: str) -> tuple[str, str, int]:
    """Asynchronously runs a shell command."""
    process = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return (
        stdout.decode('utf-8', 'replace').strip(),
        stderr.decode('utf-8', 'replace').strip(),
        process.returncode
    )

def sync_resize_image(input_path: str, width: int, height: int) -> str:
    """Resizes a static image using Pillow."""
    base, ext = os.path.splitext(os.path.basename(input_path))
    output_path = os.path.join(TEMP_DIR, f"{base}_resized{ext}")
    
    with Image.open(input_path) as img:
        resized_img = img.resize((width, height), Image.Resampling.LANCZOS)
        if resized_img.mode in ("RGBA", "P"):
            resized_img = resized_img.convert("RGB")
        resized_img.save(output_path)
    return output_path

async def sync_resize_video_or_gif(input_path: str, width: int, height: int) -> str:
    """Resizes a video or GIF using FFmpeg."""
    base, ext = os.path.splitext(os.path.basename(input_path))
    output_path = os.path.join(TEMP_DIR, f"{base}_resized{ext}")
    
    command = f'ffmpeg -i "{input_path}" -vf "scale={width}:{height}" -y "{output_path}"'
    
    _, stderr, returncode = await run_command(command)
    if returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {stderr}")
    return output_path


@bot.add_cmd(cmd="resize")
async def resize_handler(bot: BOT, message: Message):
    """
    CMD: RESIZE
    INFO: Resizes an image, GIF, or video.
    USAGE: .resize [width]x[height] (reply to media)
    """
    replied_msg = message.replied
    if not replied_msg or not replied_msg.media:
        await message.edit("Please reply to an image, GIF, or video to resize it.", del_in=ERROR_VISIBLE_DURATION)
        return

    if not message.input:
        await message.edit("Please specify the new resolution. Usage: `.resize 1920x1080`", del_in=ERROR_VISIBLE_DURATION)
        return

    try:
        width_str, height_str = message.input.lower().split('x')
        width, height = int(width_str), int(height_str)
        if not (0 < width <= 8192 and 0 < height <= 8192):
            raise ValueError("Dimensions must be between 1 and 8192.")
    except (ValueError, IndexError):
        await message.edit("Invalid resolution format. Please use `[width]x[height]`.", del_in=ERROR_VISIBLE_DURATION)
        return

    progress_message = await message.reply("<code>Downloading media...</code>")
    
    original_path, resized_path = "", ""
    try:
        original_path = await bot.download_media(replied_msg)
        await progress_message.edit(f"<code>Resizing to {width}x{height}...</code>")
        
        if replied_msg.photo:
            resized_path = await asyncio.to_thread(sync_resize_image, original_path, width, height)
            await bot.send_photo(message.chat.id, photo=resized_path, caption=f"Resized to: `{width}x{height}`")
        
        elif replied_msg.video or replied_msg.animation:
            resized_path = await sync_resize_video_or_gif(original_path, width, height)
            if replied_msg.video:
                await bot.send_video(message.chat.id, video=resized_path, caption=f"Resized to: `{width}x{height}`")
            else:
                await bot.send_animation(message.chat.id, animation=resized_path, caption=f"Resized to: `{width}x{height}`")
        else:
            raise ValueError("Unsupported media type. Please reply to an image, GIF, or video.")
        
        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not resize media.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
        try: await message.delete()
        except: pass
    finally:
        if original_path and os.path.exists(original_path): os.remove(original_path)
        if resized_path and os.path.exists(resized_path): os.remove(resized_path)
