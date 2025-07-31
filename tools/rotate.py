import os
import html
import asyncio
import math
from PIL import Image
from pyrogram.types import Message, ReplyParameters

from app import BOT, bot

TEMP_DIR = "temp_rotate/"
os.makedirs(TEMP_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 8

async def run_command(command: str) -> tuple[str, str, int]:
    process = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return (
        stdout.decode('utf-8', 'replace').strip(),
        stderr.decode('utf-8', 'replace').strip(),
        process.returncode
    )

def sync_rotate_image(input_path: str, angle: float) -> str:
    base, ext = os.path.splitext(os.path.basename(input_path))
    output_path = os.path.join(TEMP_DIR, f"{base}_rotated.png")
    
    with Image.open(input_path) as img:
        rotated_img = img.rotate(-angle, expand=True, fillcolor='black')
        
        if rotated_img.mode == "RGBA":
            final_img = Image.new("RGB", rotated_img.size, "black")
            final_img.paste(rotated_img, (0, 0), rotated_img)
        else:
            final_img = rotated_img.convert("RGB")
            
        final_img.save(output_path, "PNG")
        
    return output_path

async def sync_rotate_video_or_gif(input_path: str, angle: float) -> str:
    base, ext = os.path.splitext(os.path.basename(input_path))
    output_path = os.path.join(TEMP_DIR, f"{base}_rotated{ext}")
    
    angle_rad = math.radians(angle)
    
    rotate_filter = (
        f"rotate={angle_rad}:c=black:ow='iw*abs(cos({angle_rad}))+ih*abs(sin({angle_rad}))':"
        f"oh='ih*abs(cos({angle_rad}))+iw*abs(sin({angle_rad}))'"
    )
    
    command = (
        f'ffmpeg -i "{input_path}" '
        f'-vf "{rotate_filter}" '
        f'-c:a copy '
        f'-y "{output_path}"'
    )

    _, stderr, code = await run_command(command)
    if code != 0:
        raise RuntimeError(f"FFmpeg rotate failed: {stderr}")
        
    return output_path


@bot.add_cmd(cmd="rotate")
async def rotate_handler(bot: BOT, message: Message):
    replied_msg = message.replied
    is_media = replied_msg and (
        replied_msg.photo or replied_msg.video or replied_msg.animation or
        (replied_msg.document and replied_msg.document.mime_type.startswith(("image/", "video/")))
    )
    if not is_media:
        return await message.edit("Please reply to an image, video, or GIF to rotate it.", del_in=ERROR_VISIBLE_DURATION)

    try:
        angle = 90.0
        if message.input:
            angle = float(message.input.strip())
    except ValueError:
        return await message.edit("Invalid angle. Please provide a number (e.g., 45, -15.5).", del_in=ERROR_VISIBLE_DURATION)

    progress_message = await message.reply("<code>Downloading media...</code>")
    
    original_path, modified_path = "", ""
    temp_files = []
    try:
        original_path = await bot.download_media(replied_msg)
        temp_files.append(original_path)
        
        await progress_message.edit(f"<code>Rotating by {angle} degrees...</code>")
        
        is_image = replied_msg.photo or (replied_msg.document and replied_msg.document.mime_type.startswith('image/'))
        is_animation = replied_msg.animation
        
        if is_image:
            modified_path = await asyncio.to_thread(sync_rotate_image, original_path, angle)
        else:
            modified_path = await sync_rotate_video_or_gif(original_path, angle)
            
        temp_files.append(modified_path)
        
        await progress_message.edit("<code>Sending media...</code>")

        caption = f"Rotated by: `{angle}°`"
        reply_params = ReplyParameters(message_id=replied_msg.id)

        if is_image:
            await bot.send_photo(message.chat.id, modified_path, caption=caption, reply_parameters=reply_params)
        elif is_animation:
            await bot.send_animation(message.chat.id, modified_path, caption=caption, reply_parameters=reply_params)
        else:
            await bot.send_video(message.chat.id, modified_path, caption=caption, reply_parameters=reply_params)
        
        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not rotate media.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
    finally:
        for f in temp_files:
            if f and os.path.exists(f):
                os.remove(f)
