import os
import html
import asyncio
import re
import shutil
import time
import math
from pyrogram.types import Message, ReplyParameters

from app import BOT, bot

TEMP_DIR = "temp_media_dl/"
os.makedirs(TEMP_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 10

ACTIVE_MEDIA_JOBS = {}

def format_bytes(size_bytes: int) -> str:
    if size_bytes == 0: return "0 B"; size_name = ("B", "KB", "MB", "GB", "TB"); i = int(math.floor(math.log(size_bytes, 1024))); p = math.pow(1024, i); s = round(size_bytes / p, 2); return f"{s} {size_name[i]}"
def format_eta(seconds: int) -> str:
    if seconds is None or seconds < 0: return "N/A"; minutes, seconds = divmod(int(seconds), 60); hours, minutes = divmod(minutes, 60)
    if hours > 0: return f"{hours:02d}:{minutes:02d}:{seconds:02d}"; return f"{minutes:02d}:{seconds:02d}"
async def progress_display(current: int, total: int, msg: Message, start: float, status: str, filename: str, job_id: int):
    elapsed = time.time() - start;
    if elapsed == 0: return
    speed = current / elapsed; percentage = current * 100 / total; eta = (total - current) / speed if speed > 0 else 0
    bar = '█' * int(10 * current // total) + '░' * (10 - int(10 * current // total))
    text = (f"<b>{status}:</b> <code>{html.escape(filename)}</code>\n\n"
            f"<code>[{bar}] {percentage:.1f}%</code>\n"
            f"<b>Progress:</b> <code>{format_bytes(current)} / {format_bytes(total)}</code>\n"
            f"<b>Speed:</b> <code>{format_bytes(speed)}/s</code> | <b>ETA:</b> <code>{format_eta(eta)}</code>\n"
            f"<b>Job ID:</b> <code>{job_id}</code>\n<i>(Use .cancelmd {job_id} to stop)</i>")
    try: await msg.edit_text(text)
    except: pass
async def run_command_with_progress(command: str, msg: Message, filename: str, job_id: int):
    process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    ACTIVE_MEDIA_JOBS[job_id]["process"] = process
    await msg.edit(f"<b>Downloading:</b> <code>{html.escape(filename)}</code>\n\n<i>Please wait, processing...</i>\n<b>Job ID:</b> <code>{job_id}</code>")
    output = await process.stdout.read()
    await process.wait()
    output_text = output.decode('utf-8', 'replace').strip()
    if process.returncode != 0:
        raise RuntimeError(f"Process failed:\n{output_text}")

async def run_command(command: str):
    process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    return (stdout.decode('utf-8', 'replace').strip(), stderr.decode('utf-8', 'replace').strip(), process.returncode)

async def media_downloader_task(link: str, progress_message: Message, job_id: int, original_message: Message):
    try:
        title_cmd = f'yt-dlp --get-title "{link}"'
        title, _, _ = await run_command(title_cmd)
        display_filename = f"{title or 'media'}"

        base_filename = str(job_id)
        output_template = f"{TEMP_DIR}{base_filename}.%(ext)s"

        command = f'yt-dlp --extractor-args "generic:impersonate=chrome110" -f "bv*+ba/b" --merge-output-format mp4 -o "{output_template}" "{link}"'
        
        await run_command_with_progress(command, progress_message, display_filename + ".mp4", job_id)

        downloaded_path = None
        for file in os.listdir(TEMP_DIR):
            if file.startswith(base_filename):
                downloaded_path = os.path.join(TEMP_DIR, file)
                break

        if not downloaded_path:
            raise FileNotFoundError("yt-dlp finished but the output file was not found.")

        caption_text = f"Downloaded: <code>{html.escape(display_filename)}</code>"
        actual_filename = os.path.basename(downloaded_path)
        is_image = actual_filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))

        start_time = time.time(); last_update = 0
        async def upload_progress(current, total):
            nonlocal last_update
            if time.time() - last_update > 5:
                await progress_display(current, total, progress_message, start_time, "Uploading", actual_filename, job_id)
                last_update = time.time()

        reply_params = ReplyParameters(message_id=original_message.id)

        if is_image:
            await bot.send_photo(chat_id=original_message.chat.id, photo=downloaded_path, caption=caption_text, reply_parameters=reply_params, progress=upload_progress)
        else:
            await bot.send_video(chat_id=original_message.chat.id, video=downloaded_path, caption=caption_text, reply_parameters=reply_params, progress=upload_progress)

        await progress_message.delete()
        try:
            await original_message.delete()
        except:
            pass
            
    except asyncio.CancelledError:
        await progress_message.edit(f"<b>Job <code>{job_id}</code> cancelled.</b>", del_in=ERROR_VISIBLE_DURATION)
    except Exception as e:
        await progress_message.edit(f"<b>Error in job <code>{job_id}</code>:</b>\n<code>{html.escape(str(e))}</code>", del_in=ERROR_VISIBLE_DURATION)
    finally:
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR, ignore_errors=True)
        os.makedirs(TEMP_DIR, exist_ok=True)


@bot.add_cmd(cmd=["media", "md"])
async def media_dl_handler(bot: BOT, message: Message):
    if not message.input:
        return await message.reply("Please provide a link from a media platform (YouTube, TikTok, etc.).", del_in=ERROR_VISIBLE_DURATION)
    link = message.input.strip()
    job_id = int(time.time())
    progress_message = await message.reply(f"<code>Starting media job {job_id}...</code>")
    task = asyncio.create_task(media_downloader_task(link, progress_message, job_id, message))
    ACTIVE_MEDIA_JOBS[job_id] = {"task": task, "process": None}
    try: await task
    finally:
        if job_id in ACTIVE_MEDIA_JOBS:
            del ACTIVE_MEDIA_JOBS[job_id]

@bot.add_cmd(cmd=["cancelmedia", "cancelmd"])
async def cancel_media_handler(bot: BOT, message: Message):
    if not message.input: return await message.reply("Please provide a Job ID to cancel.", del_in=ERROR_VISIBLE_DURATION)
    try:
        job_id = int(message.input.strip())
        if job_id in ACTIVE_MEDIA_JOBS:
            if ACTIVE_MEDIA_JOBS[job_id].get("process"):
                try: ACTIVE_MEDIA_JOBS[job_id]["process"].kill()
                except: pass
            ACTIVE_MEDIA_JOBS[job_id]["task"].cancel()
            await message.delete()
        else: await message.reply(f"Job <code>{job_id}</code> not found or already completed.", del_in=ERROR_VISIBLE_DURATION)
    except (ValueError, KeyError): await message.reply("Invalid Job ID.", del_in=ERROR_VISIBLE_DURATION)
