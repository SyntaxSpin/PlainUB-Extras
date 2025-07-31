import os
import html
import asyncio
import re
import requests
import shutil
import time
import math
from urllib.parse import unquote, urlparse
from pyrogram.types import Message, ReplyParameters

from app import BOT, bot

TEMP_DIR = "temp_downloader/"
os.makedirs(TEMP_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 10

# Global dictionary to keep track of active download/upload tasks
ACTIVE_JOBS = {}

def format_bytes(size_bytes: int) -> str:
    if size_bytes == 0: return "0 B"; size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024))); p = math.pow(1024, i)
    s = round(size_bytes / p, 2); return f"{s} {size_name[i]}"

def format_eta(seconds: int) -> str:
    if seconds is None or seconds < 0: return "N/A"
    minutes, seconds = divmod(int(seconds), 60); hours, minutes = divmod(minutes, 60)
    if hours > 0: return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

async def progress_display(current: int, total: int, msg: Message, start: float, status: str, filename: str, job_id: int):
    elapsed = time.time() - start; if elapsed == 0: return
    speed = current / elapsed; percentage = current * 100 / total
    eta = (total - current) / speed if speed > 0 else 0
    bar = '█' * int(10 * current // total) + '░' * (10 - int(10 * current // total))
    text = (f"<b>{status}:</b> <code>{html.escape(filename)}</code>\n\n"
            f"<code>[{bar}] {percentage:.1f}%</code>\n"
            f"<b>Progress:</b> <code>{format_bytes(current)} / {format_bytes(total)}</code>\n"
            f"<b>Speed:</b> <code>{format_bytes(speed)}/s</code> | <b>ETA:</b> <code>{format_eta(eta)}</code>\n"
            f"<b>Job ID:</b> <code>{job_id}</code>\n<i>(Use .cancel {job_id} to stop)</i>")
    try: await msg.edit_text(text)
    except: pass

async def downloader_task(message: Message, progress_message: Message, job_id: int):
    temp_files = []
    try:
        source = message.input.strip() if message.input else message.replied
        filename = "Unknown"

        if isinstance(source, str): # It's a link
            if is_youtube_link(source):
                title_cmd = f'yt-dlp --get-title "{source}"'
                filename, _, _ = await run_command(title_cmd); filename += ".mp4"
                command = f'yt-dlp --progress -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" --merge-output-format mp4 -o "{TEMP_DIR}{filename}" "{source}"'
                await run_command_with_progress(command, progress_message, filename, job_id)
                downloaded_path = os.path.join(TEMP_DIR, filename)
            elif is_magnet_link(source):
                filename = "Torrent Download"
                command = f'aria2c --summary-interval=1 --seed-time=0 -d "{TEMP_DIR}" "{source}"'
                await run_command_with_progress(command, progress_message, filename, job_id)
                files = [f for f in os.listdir(TEMP_DIR) if not f.endswith((".aria2", ".torrent"))]
                if len(files) == 1: downloaded_path = os.path.join(TEMP_DIR, files[0])
                else:
                    await progress_message.edit("<code>Zipping torrent files...</code>")
                    zip_out = os.path.join(TEMP_DIR, "torrent_download"); shutil.make_archive(zip_out, 'zip', TEMP_DIR)
                    downloaded_path = zip_out + ".zip"
            elif is_http_link(source):
                downloaded_path = await _download_http(source, progress_message, job_id)
            else: raise ValueError("Unsupported link type.")
        else: # It's a replied media message
            media_obj = (source.photo or source.video or source.animation or source.document or source.audio or source.voice)
            filename = getattr(media_obj, 'file_name', "replied_media")
            await progress_message.edit(f"<code>Downloading: {html.escape(filename)}</code>")
            downloaded_path = await bot.download_media(source)

        temp_files.append(downloaded_path)
        filename = os.path.basename(downloaded_path)

        start_time = time.time(); last_update = 0
        async def upload_progress(current, total):
            nonlocal last_update
            if time.time() - last_update > 5:
                await progress_display(current, total, progress_message, start_time, "Uploading", filename, job_id)
                last_update = time.time()
        
        reply_params = ReplyParameters(message_id=message.id if message.input else source.id)
        await bot.send_document(
            chat_id=message.chat.id, document=downloaded_path,
            caption=f"Downloaded: <code>{filename}</code>",
            reply_parameters=reply_params, progress=upload_progress
        )
        await progress_message.delete(); await message.delete()

    except asyncio.CancelledError:
        await progress_message.edit(f"<b>Job <code>{job_id}</code> cancelled successfully.</b>", del_in=ERROR_VISIBLE_DURATION)
    except Exception as e:
        await progress_message.edit(f"<b>Error in job <code>{job_id}</code>:</b>\n<code>{html.escape(str(e))}</code>", del_in=ERROR_VISIBLE_DURATION)
    finally:
        shutil.rmtree(TEMP_DIR, ignore_errors=True); os.makedirs(TEMP_DIR, exist_ok=True)

async def run_command(command: str):
    process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    return (stdout.decode('utf-8', 'replace').strip(), stderr.decode('utf-8', 'replace').strip(), process.returncode)
async def run_command_with_progress(command: str, msg: Message, filename: str, job_id: int):
    process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    last_update = 0; output_lines = []
    while True:
        line = await process.stdout.readline();
        if not line: break
        line_text = line.decode('utf-8', 'replace').strip(); output_lines.append(line_text)
        if time.time() - last_update > 5:
            display_text = "\n".join(output_lines[-5:])
            await msg.edit(f"<b>Downloading:</b> <code>{html.escape(filename)}</code>\n\n<code>{html.escape(display_text)}</code>\n<b>Job ID:</b> <code>{job_id}</code>")
            last_update = time.time()
    await process.wait();
    if process.returncode != 0: raise RuntimeError(f"Process failed:\n{'\n'.join(output_lines)}")
async def _download_http(link: str, msg: Message, job_id: int):
    with requests.get(link, stream=True) as r:
        r.raise_for_status()
        filename = os.path.basename(unquote(urlparse(link).path)) or "downloaded_file"
        file_path = os.path.join(TEMP_DIR, filename)
        total_size = int(r.headers.get('content-length', 0))
        downloaded = 0; start_time = time.time(); last_update = 0
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk); downloaded += len(chunk)
                if time.time() - last_update > 5 and total_size > 0:
                    await progress_display(downloaded, total_size, msg, start_time, "Downloading", filename, job_id)
                    last_update = time.time()
    return file_path
def is_youtube_link(url: str): return bool(re.match(r"(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+", url))
def is_magnet_link(url: str): return url.startswith("magnet:?")
def is_http_link(url: str): return url.startswith(("http://", "https://"))

@bot.add_cmd(cmd=["downloader", "dl"])
async def downloader_handler(bot: BOT, message: Message):
    if not message.input and not (message.replied and message.replied.media):
        return await message.edit("Please provide a link or reply to a file to download.", del_in=ERROR_VISIBLE_DURATION)

    job_id = int(time.time())
    progress_message = await message.reply(f"<code>Starting job {job_id}...</code>")
    
    task = asyncio.create_task(downloader_task(message, progress_message, job_id))
    ACTIVE_JOBS[job_id] = task
    
    try:
        await task
    finally:
        if job_id in ACTIVE_JOBS:
            del ACTIVE_JOBS[job_id]

@bot.add_cmd(cmd="cancel")
async def cancel_handler(bot: BOT, message: Message):
    if not message.input:
        return await message.edit("Please provide a Job ID to cancel.", del_in=ERROR_VISIBLE_DURATION)
    try:
        job_id = int(message.input.strip())
        if job_id in ACTIVE_JOBS:
            ACTIVE_JOBS[job_id].cancel()
            # The cleanup and final message are handled in the task's exception block
            await message.delete()
        else:
            await message.edit(f"Job <code>{job_id}</code> not found or already completed.", del_in=ERROR_VISIBLE_DURATION)
    except ValueError:
        await message.edit("Invalid Job ID.", del_in=ERROR_VISIBLE_DURATION)
