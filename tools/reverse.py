import os
import html
import asyncio
from pyrogram.types import Message, ReplyParameters

from app import BOT, bot

TEMP_DIR = "temp_reverse/"
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

async def sync_reverse_media(input_path: str, is_video: bool) -> str:
    """
    Synchronously reverses a video or audio file using FFmpeg.
    """
    base, ext = os.path.splitext(os.path.basename(input_path))
    output_path = os.path.join(TEMP_DIR, f"{base}_reversed{ext}")
    
    command = ""
    if is_video:
        command = (
            f'ffmpeg -i "{input_path}" '
            f'-vf "reverse" -af "areverse" '
            f'-y "{output_path}"'
        )
    else: # Audio only
        command = (
            f'ffmpeg -i "{input_path}" '
            f'-af "areverse" '
            f'-y "{output_path}"'
        )

    _, stderr, code = await run_command(command)
    
    if code != 0:
        if is_video and ("Cannot find a matching stream" in stderr or "anull" in stderr):
            command = (
                f'ffmpeg -i "{input_path}" '
                f'-vf "reverse" -an '
                f'-y "{output_path}"'
            )
            _, stderr_fallback, code_fallback = await run_command(command)
            if code_fallback != 0: raise RuntimeError(f"FFmpeg reverse failed (no audio): {stderr_fallback}")
        else:
            raise RuntimeError(f"FFmpeg reverse failed: {stderr}")
        
    return output_path


@bot.add_cmd(cmd="reverse")
async def reverse_handler(bot: BOT, message: Message):
    """
    CMD: REVERSE
    INFO: Reverses the replied video or audio file.
    USAGE:
        .reverse
    """
    replied_msg = message.replied
    is_media = replied_msg and (replied_msg.video or replied_msg.audio or replied_msg.voice or (replied_msg.document and replied_msg.document.mime_type.startswith(("video/", "audio/"))))
    if not is_media:
        return await message.edit("Please reply to a video or audio file.", del_in=ERROR_VISIBLE_DURATION)

    progress_message = await message.reply("<code>Downloading media...</code>")
    
    original_path, modified_path = "", ""
    temp_files = []
    try:
        media_object = (replied_msg.video or replied_msg.audio or replied_msg.voice or replied_msg.document)
        original_path = await bot.download_media(media_object)
        temp_files.append(original_path)
        
        is_video = bool(replied_msg.video or (replied_msg.document and replied_msg.document.mime_type.startswith('video/')))
        
        await progress_message.edit("<code>Reversing...</code>")
        
        modified_path = await sync_reverse_media(original_path, is_video)
        temp_files.append(modified_path)
        
        await progress_message.edit("<code>Sending media...</code>")

        caption = "Reversed!"
        reply_params = ReplyParameters(message_id=replied_msg.id)

        if is_video:
            await bot.send_video(message.chat.id, modified_path, caption=caption, reply_parameters=reply_params)
        elif replied_msg.voice:
             await bot.send_voice(message.chat.id, modified_path, caption=caption, reply_parameters=reply_params)
        else: # Audio
            await bot.send_audio(message.chat.id, modified_path, caption=caption, reply_parameters=reply_params)
        
        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not reverse media.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
    finally:
        for f in temp_files:
            if f and os.path.exists(f): os.remove(f)
