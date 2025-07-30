import os
import html
import asyncio
import re
from pyrogram.types import Message

from app import BOT, bot

TEMP_DIR = "temp_speed/"
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

async def sync_change_speed(input_path: str, speed_factor: float) -> str:
    """
    Synchronously changes the speed of a video or audio file using FFmpeg.
    """
    base, ext = os.path.splitext(os.path.basename(input_path))
    output_path = os.path.join(TEMP_DIR, f"{base}_speed_{speed_factor}x{ext}")
    
    video_filter = f'[0:v]setpts={1/speed_factor}*PTS[v]'
    audio_filter = f'[0:a]atempo={speed_factor}[a]'
    
    
    command = (
        f'ffmpeg -i "{input_path}" '
        f'-filter_complex "{video_filter};{audio_filter}" '
        f'-map "[v]" -map "[a]" '
        f'-y "{output_path}"'
    )
    
    if not input_path.lower().endswith(('.mp4', '.mkv', '.mov', '.webm')):
         command = (
            f'ffmpeg -i "{input_path}" '
            f'-filter:a "atempo={speed_factor}" '
            f'-y "{output_path}"'
        )

    _, stderr, code = await run_command(command)
    if code != 0:
        if "Cannot find a matching stream for unlabeled input pad 1 on filter Parsed_atempo" in stderr:
            command = (
                f'ffmpeg -i "{input_path}" '
                f'-filter:v "setpts={1/speed_factor}*PTS" -an '
                f'-y "{output_path}"'
            )
            _, stderr, code = await run_command(command)
            if code != 0: raise RuntimeError(f"FFmpeg speed change failed even without audio: {stderr}")
        else:
            raise RuntimeError(f"FFmpeg speed change failed: {stderr}")
        
    return output_path


@bot.add_cmd(cmd="speed")
async def speed_handler(bot: BOT, message: Message):
    """
    CMD: SPEED
    INFO: Speeds up or slows down the replied video/audio.
    USAGE:
        .speed <factor> (e.g., .speed 2 for 2x faster, .speed 0.5 for 2x slower)
    """
    replied_msg = message.replied
    is_media = replied_msg and (replied_msg.video or replied_msg.audio or replied_msg.voice or (replied_msg.document and replied_msg.document.mime_type.startswith(("video/", "audio/"))))
    if not is_media:
        return await message.edit("Please reply to a video or audio file.", del_in=ERROR_VISIBLE_DURATION)

    if not message.input:
        return await message.edit("Please specify a speed factor. Usage: `.speed 2.0`", del_in=ERROR_VISIBLE_DURATION)

    try:
        speed_factor = float(message.input)
        if not (0.5 <= speed_factor <= 4.0):
            raise ValueError("Speed factor must be between 0.5 and 4.0 for this tool.")
    except ValueError:
        return await message.edit("Invalid speed factor. Please use a number like `2.0` or `0.5`.", del_in=ERROR_VISIBLE_DURATION)

    progress_message = await message.reply("<code>Downloading media...</code>")
    
    original_path, modified_path = "", ""
    temp_files = []
    try:
        original_path = await bot.download_media(replied_msg)
        temp_files.append(original_path)
        
        await progress_message.edit(f"<code>Changing speed to {speed_factor}x...</code>")
        
        modified_path = await sync_change_speed(original_path, speed_factor)
        temp_files.append(modified_path)
        
        await progress_message.edit("<code>Sending media...</code>")

        caption = f"Speed changed to: `{speed_factor}x`"
        
        if replied_msg.video or (replied_msg.document and replied_msg.document.mime_type.startswith("video/")):
            await bot.send_video(message.chat.id, video=modified_path, caption=caption, reply_to_message_id=replied_msg.id)
        elif replied_msg.voice:
             await bot.send_voice(message.chat.id, voice=modified_path, caption=caption, reply_to_message_id=replied_msg.id)
        else: # Audio
            await bot.send_audio(message.chat.id, audio=modified_path, caption=caption, reply_to_message_id=replied_msg.id)
        
        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not change speed.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
    finally:
        for f in temp_files:
            if f and os.path.exists(f): os.remove(f)
