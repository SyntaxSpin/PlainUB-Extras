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
ACTIVE_DL_JOBS = {}

# --- Helper Functions ---
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
            f"<b>Speed:</b> <code>{format_bytes(speed)}/s</code> | <b>ETA:</b> <code>{format_eta(eta)}</code>\n"
            f"<b>Job ID:</b> <code>{job_id}</code>\n<i>(Use .canceldl {job_id} to stop)</i>")
    try: await msg.edit_text(text)
    except: pass
async def run_command_with_progress(command: str, msg: Message, filename: str, job_id: int):
    process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    ACTIVE_DL_JOBS[job_id]["process"] = process
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

# --- Specialized Downloaders ---
async def _download_http(link: str, msg: Message, job_id: int):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    with requests.get(link, stream=True, headers=headers) as r:
        r.raise_for_status()
        filename = os.path.basename(unquote(urlparse(r.url).path)) or "downloaded_file"
        file_path = os.path.join(TEMP_DIR, filename)
        total_size = int(r.headers.get('content-length', 0))
        downloaded = 0; start_time = time.time(); last_update = 0
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if job_id not in ACTIVE_DL_JOBS: raise asyncio.CancelledError
                f.write(chunk); downloaded += len(chunk)
                if time.time() - last_update > 5 and total_size > 0:
                    await progress_display(downloaded, total_size, msg, start_time, "Downloading", filename, job_id)
                    last_update = time.time()
    return file_path
async def _download_torrent(link: str, msg: Message, job_id: int):
    command = f'aria2c --summary-interval=1 --seed-time=0 -d "{TEMP_DIR}" "{link}"'
    await run_command_with_progress(command, msg, "Torrent Download", job_id)
    files = [f for f in os.listdir(TEMP_DIR) if not f.endswith((".aria2", ".torrent"))]
    if len(files) == 1: return os.path.join(TEMP_DIR, files[0])
    elif len(files) > 1:
        await msg.edit("<code>Zipping torrent files...</code>")
        zip_out = os.path.join(TEMP_DIR, "torrent_download"); shutil.make_archive(zip_out, 'zip', TEMP_DIR)
        return zip_out + ".zip"
    raise FileNotFoundError("Could not find any downloaded files from the torrent.")

# --- Link Detection ---
def is_magnet_link(url: str): return url.startswith("magnet:?")
def is_http_link(url: str): return url.startswith(("http://", "https://"))

# --- Main Task ---
async def downloader_task(link: str, progress_message: Message, job_id: int, original_message: Message):
    try:
        if is_magnet_link(link): downloaded_path = await _download_torrent(link, progress_message, job_id)
        elif is_http_link(link): downloaded_path = await _download_http(link, progress_message, job_id)
        else: raise ValueError("Unsupported link type. Only HTTP and Magnet links are supported by this command.")
        
        filename = os.path.basename(downloaded_path)
        start_time = time.time(); last_update = 0
        async def upload_progress(current, total):
            nonlocal last_update
            if time.time() - last_update > 5:
                await progress_display(current, total, progress_message, start_time, "Uploading", filename, job_id)
                last_update = time.time()
        
        reply_params = ReplyParameters(message_id=original_message.id)
        await bot.send_document(chat_id=original_message.chat_id, document=downloaded_path, caption=f"Downloaded: <code>{filename}</code>", reply_parameters=reply_params, progress=upload_progress)
        await progress_message.delete(); await original_message.delete()
    except asyncio.CancelledError:
        await progress_message.edit(f"<b>Job <code>{job_id}</code> cancelled.</b>", del_in=ERROR_VISIBLE_DURATION)
    except Exception as e:
        await progress_message.edit(f"<b>Error in job <code>{job_id}</code>:</b>\n<code>{html.escape(str(e))}</code>", del_in=ERROR_VISIBLE_DURATION)
    finally:
        shutil.rmtree(TEMP_DIR, ignore_errors=True); os.makedirs(TEMP_DIR, exist_ok=True)

# --- Main Handlers ---
@bot.add_cmd(cmd=["download", "dl"])
async def dl_handler(bot: BOT, message: Message):
    if not message.input:
        return await message.edit("Please provide a direct HTTP or Magnet link.", del_in=ERROR_VISIBLE_DURATION)
    link = message.input.strip()
    job_id = int(time.time())
    progress_message = await message.reply(f"<code>Starting download job {job_id}...</code>")
    task = asyncio.create_task(downloader_task(link, progress_message, job_id, message))
    ACTIVE_DL_JOBS[job_id] = {"task": task, "process": None}
    try: await task
    finally:
        if job_id in ACTIVE_DL_JOBS: del ACTIVE_DL_JOBS[job_id]

@bot.add_cmd(cmd=["canceldl"])
async def cancel_dl_handler(bot: BOT, message: Message):
    if not message.input: return await message.edit("Please provide a Job ID to cancel.", del_in=ERROR_VISIBLE_DURATION)
    try:
        job_id = int(message.input.strip())
        if job_id in ACTIVE_DL_JOBS:
            if ACTIVE_DL_JOBS[job_id].get("process"):
                try: ACTIVE_DL_JOBS[job_id]["process"].kill()
                except: pass
            ACTIVE_DL_JOBS[job_id]["task"].cancel()
            await message.delete()
        else: await message.edit(f"Job <code>{job_id}</code> not found or already completed.", del_in=ERROR_VISIBLE_DURATION)
    except (ValueError, KeyError): await message.edit("Invalid Job ID.", del_in=ERROR_VISIBLE_DURATION)
