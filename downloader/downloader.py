import os
import html
import asyncio
import re
import requests
import shutil
import time
import math
from urllib.parse import unquote, urlparse
from pyrogram.types import Message

from app import BOT, bot

UBOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOWNLOADS_DIR = os.path.join(UBOT_DIR, "downloads/")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 10
ACTIVE_JOBS = {}

def format_bytes(size_bytes: int) -> str:
    if size_bytes <= 0: return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def format_eta(seconds: int) -> str:
    if seconds is None or seconds < 0: return "N/A"
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0: return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

async def progress_display(msg: Message, status: str, filename: str, job_id: int, current: int, total: int, start: float):
    elapsed = time.time() - start
    if elapsed == 0: return
    speed = current / elapsed
    
    if total <= 0:
        text = (f"<b>{status}:</b> <code>{html.escape(filename)}</code>\n\n"
                f"<b>Progress:</b> <code>{format_bytes(current)} / ???</code>\n"
                f"<b>Speed:</b> <code>{format_bytes(speed)}/s</code> | <b>ETA:</b> <code>N/A</code>\n"
                f"<b>Job ID:</b> <code>{job_id}</code>\n<i>(Use .canceldl {job_id} to stop)</i>")
    else:
        percentage = current * 100 / total
        eta = (total - current) / speed if speed > 0 else 0
        bar = '█' * int(10 * percentage // 100) + '░' * (10 - int(10 * percentage // 100))
        text = (f"<b>{status}:</b> <code>{html.escape(filename)}</code>\n\n"
                f"<code>[{bar}] {percentage:.1f}%</code>\n"
                f"<b>Progress:</b> <code>{format_bytes(current)} / {format_bytes(total)}</code>\n"
                f"<b>Speed:</b> <code>{format_bytes(speed)}/s</code> | <b>ETA:</b> <code>{format_eta(eta)}</code>\n"
                f"<b>Job ID:</b> <code>{job_id}</code>\n<i>(Use .canceldl {job_id} to stop)</i>")
    try:
        await msg.edit_text(text)
    except:
        pass

async def downloader_task(link: str, progress_message: Message, job_id: int):
    file_path = None
    filename = "download"
    try:
        if link.startswith("magnet:?"):
            command = f'aria2c --console-log-level=warn --summary-interval=1 --seed-time=0 -d "{DOWNLOADS_DIR}" "{link}"'
            process = await asyncio.create_subprocess_shell(command)
            ACTIVE_JOBS[job_id]["process"] = process
            await progress_message.edit_text(f"<b>Downloading Torrent...</b>\n\n<i>(Progress is not available for torrents)</i>\n<b>Job ID:</b> <code>{job_id}</code>")
            await process.wait()
            if process.returncode != 0: raise RuntimeError("Aria2c process failed.")
            filename = "Torrent download"
        
        elif link.startswith(("http://", "https://")):
            headers = {'User-Agent': 'Mozilla/5.0'}
            with requests.get(link, stream=True, headers=headers, timeout=20) as r:
                r.raise_for_status()
                
                if "content-disposition" in r.headers:
                    d = r.headers['content-disposition']
                    filenames = re.findall('filename="?(.+?)"?$', d)
                    if filenames: filename = unquote(filenames[0])
                if filename == "download":
                    parsed_path = unquote(urlparse(r.url).path)
                    if os.path.basename(parsed_path): filename = os.path.basename(parsed_path)
                    else: filename = f"download_{job_id}"

                file_path = os.path.join(DOWNLOADS_DIR, filename)
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0
                start_time = time.time()
                last_update = 0
                
                with open(file_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        await asyncio.sleep(0)
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if time.time() - last_update > 2:
                                await progress_display(progress_message, "Downloading", filename, job_id, downloaded, total_size, start_time)
                                last_update = time.time()
        else:
            raise ValueError("Unsupported link type. Use .dl for HTTP/Magnet or .media for platform videos.")
        
        await progress_message.edit(f"✅ <b>Download complete!</b>\nFile saved: <code>{html.escape(filename)}</code>", del_in=20)

    except asyncio.CancelledError:
        await progress_message.edit(f"<b>Job <code>{job_id}</code> cancelled.</b>", del_in=ERROR_VISIBLE_DURATION)
    except Exception as e:
        await progress_message.edit(f"<b>Error in job <code>{job_id}</code>:</b>\n<code>{html.escape(str(e))}</code>", del_in=ERROR_VISIBLE_DURATION)
    finally:
        if file_path and os.path.exists(file_path):
            if "complete" not in await progress_message.get_text():
                try: os.remove(file_path)
                except OSError: pass

@bot.add_cmd(cmd=["downloader", "dl"])
async def downloader_handler(bot: BOT, message: Message):
    if not message.input:
        return await message.reply("<b>Usage:</b> .dl [http/magnet link]", del_in=ERROR_VISIBLE_DURATION)
    job_id = int(time.time())
    progress = await message.reply(f"<code>Starting job {job_id}...</code>")
    task = asyncio.create_task(downloader_task(message.input.strip(), progress, job_id))
    ACTIVE_JOBS[job_id] = {"task": task, "process": None}
    try: await task
    finally:
        if job_id in ACTIVE_JOBS: del ACTIVE_JOBS[job_id]
        try: await message.delete()
        except: pass

@bot.add_cmd(cmd="canceldl")
async def cancel_handler(bot: BOT, message: Message):
    if not message.input: return await message.reply("Please provide a Job ID.", del_in=ERROR_VISIBLE_DURATION)
    try:
        job_id = int(message.input.strip())
        if job_id in ACTIVE_JOBS:
            if ACTIVE_JOBS[job_id].get("process"):
                try: ACTIVE_JOBS[job_id]["process"].kill()
                except: pass
            ACTIVE_JOBS[job_id]["task"].cancel()
            await message.delete()
        else: await message.reply(f"Job <code>{job_id}</code> not found or already completed.", del_in=ERROR_VISIBLE_DURATION)
    except (ValueError, KeyError): await message.reply("Invalid Job ID.", del_in=ERROR_VISIBLE_DURATION)
