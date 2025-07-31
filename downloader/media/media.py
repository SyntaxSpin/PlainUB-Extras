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
    if seconds is None or seconds < 0:
        return "N/A"
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

def parse_yt_dlp_size(size_str: str) -> int:
    match = re.match(r'([0-9.]+)\s*(\w+B)', size_str, re.IGNORECASE)
    if not match: return 0
    value, unit = float(match.group(1)), match.group(2).upper()
    unit_map = {'B': 1, 'KB': 10**3, 'KIB': 1024, 'MB': 10**6, 'MIB': 1024**2, 'GB': 10**9, 'GIB': 1024**3}
    return int(value * unit_map.get(unit, 1))

async def progress_display(current: int, total: int, msg: Message, start: float, status: str, filename: str, job_id: int):
    elapsed = time.time() - start
    if elapsed == 0: return
    speed = current / elapsed
    percentage = current * 100 / total if total > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0
    bar = '█' * int(10 * percentage // 100) + '░' * (10 - int(10 * percentage // 100))
    text = (f"<b>{status}:</b> <code>{html.escape(filename)}</code>\n\n"
            f"<code>[{bar}] {percentage:.1f}%</code>\n"
            f"<b>Progress:</b> <code>{format_bytes(current)} / {format_bytes(total)}</code>\n"
            f"<b>Speed:</b> <code>{format_bytes(speed)}/s</code> | <b>ETA:</b> <code>{format_eta(eta)}</code>\n"
            f"<b>Job ID:</b> <code>{job_id}</code>\n<i>(Use .cancelmd {job_id} to stop)</i>")
    try:
        await msg.edit_text(text)
    except:
        pass

async def run_command_with_progress(command: str, msg: Message, filename: str, job_id: int):
    process = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    ACTIVE_MEDIA_JOBS[job_id]["process"] = process
    
    progress_regex = re.compile(
        r"\[download\]\s+"
        r"([0-9.]+?)%\s+of\s+~?\s*([0-9.]+\w{1,3}B)\s+at\s+([0-9.]+\w{1,3}B/s)\s+ETA\s+([0-9:]{4,})"
    )
    
    last_update = 0
    await msg.edit_text(f"<b>Downloading:</b> <code>{html.escape(filename)}</code>\n\n<i>Initializing...</i>\n<b>Job ID:</b> <code>{job_id}</code>")
    output_lines = []

    while True:
        await asyncio.sleep(0)
        try:
            line = await asyncio.wait_for(process.stdout.readline(), timeout=1.0)
        except asyncio.TimeoutError:
            if process.returncode is not None: break
            else: continue

        if not line: break
        
        line_text = line.decode('utf-8', 'replace').strip()
        output_lines.append(line_text)
        
        match = progress_regex.search(line_text)
        if match and time.time() - last_update > 2:
            percentage = float(match.group(1))
            total_size_str = match.group(2)
            speed_str = match.group(3)
            eta_str = match.group(4)
            
            total_bytes = parse_yt_dlp_size(total_size_str)
            current_bytes = int((total_bytes * percentage) / 100)
            
            bar = '█' * int(percentage // 10) + '░' * (10 - int(percentage // 10))
            text = (f"<b>Downloading:</b> <code>{html.escape(filename)}</code>\n\n"
                    f"<code>[{bar}] {percentage:.1f}%</code>\n"
                    f"<b>Progress:</b> <code>{format_bytes(current_bytes)} / {total_size_str}</code>\n"
                    f"<b>Speed:</b> <code>{speed_str}</code> | <b>ETA:</b> <code>{eta_str}</code>\n"
                    f"<b>Job ID:</b> <code>{job_id}</code>\n<i>(Use .cancelmd {job_id} to stop)</i>")
            
            try: await msg.edit_text(text)
            except: pass
            last_update = time.time()

    await process.wait()
    if process.returncode != 0:
        raise RuntimeError(f"Process failed:\n{html.escape('\n'.join(output_lines[-5:]))}")

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
        
        command = f'yt-dlp --progress --newline --extractor-args "generic:impersonate=chrome110" -f "bv*+ba/b" --merge-output-format mp4 -o "{output_template}" "{link}"'
        
        await run_command_with_progress(command, progress_message, display_filename, job_id)
        
        downloaded_path = None
        for file in os.listdir(TEMP_DIR):
            if file.startswith(base_filename):
                downloaded_path = os.path.join(TEMP_DIR, file)
                break
        
        if not downloaded_path:
            raise FileNotFoundError("yt-dlp finished but the output file was not found.")

        actual_filename = os.path.basename(downloaded_path)
        is_image = actual_filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))

        start_time = time.time(); last_update = 0
        async def upload_progress(current, total):
            nonlocal last_update
            if time.time() - last_update > 5:
                await progress_display(current, total, progress_message, start_time, "Uploading", actual_filename, job_id)
                last_update = time.time()

        reply_params = ReplyParameters(message_id=original_message.id)
        caption = f"Downloaded: <code>{html.escape(display_filename)}</code>"
        
        if is_image:
            await bot.send_photo(chat_id=original_message.chat.id, photo=downloaded_path, caption=caption, reply_parameters=reply_params, progress=upload_progress)
        else:
            await bot.send_video(chat_id=original_message.chat.id, video=downloaded_path, caption=caption, reply_parameters=reply_params, progress=upload_progress)
        
        await progress_message.delete(); await original_message.delete()
    except asyncio.CancelledError:
        await progress_message.edit(f"<b>Job <code>{job_id}</code> cancelled.</b>", del_in=ERROR_VISIBLE_DURATION)
    except Exception as e:
        await progress_message.edit(f"<b>Error in job <code>{job_id}</code>:</b>\n<code>{html.escape(str(e))}</code>", del_in=ERROR_VISIBLE_DURATION)
    finally:
        shutil.rmtree(TEMP_DIR, ignore_errors=True); os.makedirs(TEMP_DIR, exist_ok=True)

@bot.add_cmd(cmd=["media", "md"])
async def media_dl_handler(bot: BOT, message: Message):
    if not message.input:
        return await message.reply("Please provide a link from a media platform (YouTube, TikTok, etc.).", del_in=ERROR_VISIBLE_DURATION)
    link = message.input.strip()
    job_id = int(time.time())
    progress_message = await message.reply(f"<code>Starting media downloading job {job_id}...</code>")
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
