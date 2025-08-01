import os
import html
import asyncio
import re
import shutil
import time
import math
import logging
from pyrogram.types import Message, ReplyParameters

from app import BOT, bot

logging.getLogger("pyrogram.session.session").setLevel(logging.ERROR)

TEMP_DIR = "temp_media/"
os.makedirs(TEMP_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 10
ACTIVE_MEDIA_JOBS = {}

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

def parse_yt_dlp_size(size_str: str) -> int:
    cleaned_size_str = size_str.lstrip('~')
    match = re.match(r'([0-9.]+)\s*(\w+B)', cleaned_size_str, re.IGNORECASE)
    if not match: return 0
    value, unit = float(match.group(1)), match.group(2).upper()
    unit_map = {'B': 1, 'KB': 1000, 'KIB': 1024, 'MB': 1000**2, 'MIB': 1024**2, 'GB': 1000**3, 'GIB': 1024**3}
    return int(value * unit_map.get(unit, 1))

async def run_command(command: str):
    process = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return (stdout.decode('utf-8', 'replace').strip(), stderr.decode('utf-8', 'replace').strip(), process.returncode)

async def media_downloader_task(link: str, progress_message: Message, job_id: int, original_message: Message, detailed_progress: bool):
    try:
        title, _, _ = await run_command(f'yt-dlp --get-title "{link}"')
        display_filename = title or "media"

        filename_template = f"'%(title).200s.%(ext)s'"
        safe_filename, stderr, ret_code = await run_command(f'yt-dlp --get-filename -o {filename_template} "{link}"')
        if ret_code != 0: raise RuntimeError(f"Could not get safe filename: {stderr}")

        output_path = os.path.join(TEMP_DIR, safe_filename)
        
        command = f'yt-dlp --progress --newline --extractor-args "generic:impersonate=chrome110" -f "bv*+ba/b" --merge-output-format mp4 -o "{output_path}" "{link}"'
        
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        ACTIVE_MEDIA_JOBS[job_id]["process"] = process
        
        progress_regex = re.compile(
            r"\[download\]\s+"
            r"([0-9.]+?)%\s+of\s+~?\s*([0-9.]+\w{1,3}B)"
            r"(?:\s+at\s+([0-9.]+\w{1,3}B/s)\s+ETA\s+([0-9:]{4,}))?"
        )
        
        last_update = 0
        simple_msg = (f"<b>Downloading:</b> <code>{html.escape(display_filename)}</code>\n\n"
                      f"<b>Job ID:</b> <code>{job_id}</code>\n(Use <code>.cancel {job_id}</code> to stop)")
        await progress_message.edit_text(simple_msg)

        while True:
            await asyncio.sleep(0)
            line = await process.stdout.readline()
            if not line: break
            
            if detailed_progress:
                line_text = line.decode('utf-8', 'replace').strip()
                status_text = f"<b>Downloading:</b> <code>{html.escape(display_filename)}</code>\n\n"
                
                if "[Merger]" in line_text:
                    bar = '█' * 10
                    status_text += f"<code>[{bar}] 100%</code>\n<b>Status:</b> <code>Processing...</code>"
                else:
                    match = progress_regex.search(line_text)
                    if match:
                        percentage = float(match.group(1))
                        total_size_str, speed_str, eta_str = match.group(2), match.group(3) or "N/A", match.group(4) or "N/A"
                        total_bytes, current_bytes = parse_yt_dlp_size(total_size_str), int(parse_yt_dlp_size(total_size_str) * percentage / 100)
                        bar = '█' * int(percentage // 10) + '░' * (10 - int(percentage // 10))
                        status_text += (f"<code>[{bar}] {percentage:.1f}%</code>\n"
                                        f"<b>Progress:</b> <code>{format_bytes(current_bytes)} / {total_size_str}</code>\n"
                                        f"<b>Speed:</b> <code>{speed_str}</code> | <b>ETA:</b> <code>{eta_str}</code>")
                    else: continue

                if time.time() - last_update > 2:
                    status_text += f"\n\n<b>Job ID:</b> <code>{job_id}</code>\n(Use <code>.cancel {job_id}</code> to stop)"
                    try: await progress_message.edit_text(status_text)
                    except: pass
                    last_update = time.time()

        await process.wait()
        if process.returncode != 0: raise RuntimeError("Download process failed.")
        if not os.path.exists(output_path): raise FileNotFoundError("Downloaded file not found.")
        
        downloaded_path = output_path
        
        upload_progress_callback = None
        if detailed_progress:
            start_time = time.time()
            last_update_time = 0
            async def upload_progress(current, total):
                nonlocal last_update_time
                if time.time() - last_update_time > 2:
                    percentage, elapsed = current * 100 / total, time.time() - start_time
                    speed = current / elapsed if elapsed > 0 else 0
                    eta = (total - current) / speed if speed > 0 else 0
                    bar = '█' * int(percentage // 10) + '░' * (10 - int(percentage // 10))
                    text = (f"<b>Uploading:</b> <code>{html.escape(os.path.basename(downloaded_path))}</code>\n\n"
                            f"<code>[{bar}] {percentage:.1f}%</code>\n"
                            f"<b>Progress:</b> <code>{format_bytes(current)} / {format_bytes(total)}</code>\n"
                            f"<b>Speed:</b> <code>{format_bytes(speed)}/s</code> | <b>ETA:</b> <code>{format_eta(eta)}</code>\n\n"
                            f"<b>Job ID:</b> <code>{job_id}</code>\n(Use <code>.cancel {job_id}</code> to stop)")
                    try: await progress_message.edit_text(text)
                    except: pass
                    last_update_time = time.time()
                return True
            upload_progress_callback = upload_progress
        else:
            simple_upload_msg = (f"<b>Uploading:</b> <code>{html.escape(os.path.basename(downloaded_path))}</code>\n\n"
                                 f"<b>Job ID:</b> <code>{job_id}</code>(Use <code>.cancel {job_id}</code> to stop)")
            await progress_message.edit_text(simple_upload_msg)

        is_image = downloaded_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        reply_params = ReplyParameters(message_id=original_message.id)
        caption = f"Downloaded: <code>{html.escape(display_filename)}</code>"

        upload_task = None
        try:
            if is_image:
                upload_task = asyncio.create_task(
                    bot.send_photo(
                        chat_id=original_message.chat.id,
                        photo=downloaded_path,
                        caption=caption,
                        reply_parameters=reply_params,
                        progress=upload_progress_callback
                    )
                )
            else:
                upload_task = asyncio.create_task(
                    bot.send_video(
                        chat_id=original_message.chat.id,
                        video=downloaded_path,
                        caption=caption,
                        reply_parameters=reply_params,
                        progress=upload_progress_callback
                    )
                )
            ACTIVE_MEDIA_JOBS[job_id]["upload_task"] = upload_task
            await upload_task
        finally:
            if "upload_task" in ACTIVE_MEDIA_JOBS.get(job_id, {}):
                del ACTIVE_MEDIA_JOBS[job_id]["upload_task"]
        
        await progress_message.delete(); await original_message.delete()
    except asyncio.CancelledError:
        await progress_message.edit(f"<b>Job <code>{job_id}</code> cancelled.</b>", del_in=ERROR_VISIBLE_DURATION)
    except Exception as e:
        await progress_message.edit(f"<b>Critical Error:</b>\n<code>{html.escape(str(e))}</code>", del_in=ERROR_VISIBLE_DURATION)
    finally:
        shutil.rmtree(TEMP_DIR, ignore_errors=True); os.makedirs(TEMP_DIR, exist_ok=True)

@bot.add_cmd(cmd=["media", "md"])
async def media_dl_handler(bot: BOT, message: Message):
    """
    CMD: MEDIA / MD
    INFO: Downloads media from various platforms (e.g., YouTube, TikTok).
    USAGE:
        .media [link]
        .media -m [link]  (Shows a detailed progress bar)
    """
    if not message.input:
        return await message.reply("Usage: `.media [-m] [link]`", del_in=ERROR_VISIBLE_DURATION)

    parts = message.input.split()
    detailed_progress = "-m" in parts
    link = " ".join([p for p in parts if p != "-m"])

    if not link:
        return await message.edit("Please provide a link.", del_in=ERROR_VISIBLE_DURATION)
    
    job_id = int(time.time())
    progress_message = await message.reply(f"<code>Starting downloading media job {job_id}...</code>")
    task = asyncio.create_task(media_downloader_task(link, progress_message, job_id, message, detailed_progress))
    ACTIVE_MEDIA_JOBS[job_id] = {"task": task, "process": None, "upload_task": None}
    try: await task
    finally:
        if job_id in ACTIVE_MEDIA_JOBS:
            del ACTIVE_MEDIA_JOBS[job_id]

@bot.add_cmd(cmd="cancel")
async def cancel_media_handler(bot: BOT, message: Message):
    """
    CMD: CANCEL
    INFO: Cancels an active media download or upload job.
    USAGE:
        .cancel [Job ID]
    """
    if not message.input: return await message.reply("Please provide a Job ID.", del_in=ERROR_VISIBLE_DURATION)
    try:
        job_id = int(message.input.strip())
        if job_id in ACTIVE_MEDIA_JOBS:
            job = ACTIVE_MEDIA_JOBS[job_id]
            if process := job.get("process"):
                try: process.kill()
                except: pass
            if upload_task := job.get("upload_task"):
                upload_task.cancel()
            job["task"].cancel()
            await message.delete()
        else: await message.reply(f"Job <code>{job_id}</code> not found.", del_in=ERROR_VISIBLE_DURATION)
    except (ValueError, KeyError): await message.reply("Invalid Job ID.", del_in=ERROR_VISIBLE_DURATION)
