import os
import html
import asyncio
import re
import requests
import shutil
from urllib.parse import unquote, urlparse
from pyrogram.types import Message, ReplyParameters

from app import BOT, bot

TEMP_DIR = "temp_downloader/"
os.makedirs(TEMP_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 10

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

def is_youtube_link(url: str) -> bool:
    return bool(re.match(r"(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+", url))

def is_magnet_link(url: str) -> bool:
    return url.startswith("magnet:?")

def is_http_link(url: str) -> bool:
    return url.startswith(("http://", "https://"))

async def _download_http(link: str, progress_message: Message):
    """Handles direct HTTP/HTTPS downloads."""
    await progress_message.edit("<code>Downloading from URL...</code>")
    
    with requests.get(link, stream=True) as r:
        r.raise_for_status()
        
        # Try to get filename from headers, then from URL
        filename = "downloaded_file"
        if "content-disposition" in r.headers:
            d = r.headers['content-disposition']
            filename = re.findall("filename=(.+)", d)[0].strip("\"'")
        else:
            filename = os.path.basename(unquote(urlparse(link).path))
            
        if not filename: filename = "downloaded_file"

        file_path = os.path.join(TEMP_DIR, filename)
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return file_path

async def _download_youtube(link: str, progress_message: Message):
    """Handles YouTube and other sites via yt-dlp."""
    await progress_message.edit("<code>Downloading via yt-dlp...</code>")
    
    # Best quality mp4 video + best quality audio, merged by ffmpeg
    command = f'yt-dlp -f "bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best" --merge-output-format mp4 -o "{TEMP_DIR}%(title)s.%(ext)s" "{link}"'
    
    stdout, stderr, code = await run_command(command)
    if code != 0:
        raise RuntimeError(f"yt-dlp failed: {stderr or stdout}")
    
    # Find the downloaded file
    for file in os.listdir(TEMP_DIR):
        if file.endswith(".mp4"): # Simple check, might need improvement for edge cases
            return os.path.join(TEMP_DIR, file)
    raise FileNotFoundError("Could not find the downloaded video file.")

async def _download_torrent(link: str, progress_message: Message):
    """Handles magnet link downloads via aria2c."""
    await progress_message.edit("<code>Starting torrent download... (this can take a long time)</code>")
    
    command = f'aria2c --seed-time=0 -d "{TEMP_DIR}" "{link}"'
    _, stderr, code = await run_command(command)
    if code != 0:
        raise RuntimeError(f"aria2c failed: {stderr}")

    # Find the downloaded file(s)
    files = [f for f in os.listdir(TEMP_DIR) if not f.endswith(".aria2")]
    if len(files) == 1:
        return os.path.join(TEMP_DIR, files[0])
    elif len(files) > 1:
        # If multiple files, zip them
        await progress_message.edit("<code>Torrent contained multiple files. Zipping...</code>")
        zip_output = os.path.join(TEMP_DIR, "torrent_download")
        shutil.make_archive(zip_output, 'zip', TEMP_DIR)
        return zip_output + ".zip"
    raise FileNotFoundError("Could not find any downloaded files from the torrent.")

@bot.add_cmd(cmd=["downloader", "dl"])
async def downloader_handler(bot: BOT, message: Message):
    if not message.input:
        return await message.edit("Please provide a link to download.", del_in=ERROR_VISIBLE_DURATION)

    link = message.input.strip()
    
    progress_message = await message.reply("<code>Analyzing link...</code>")
    
    downloaded_path = ""
    temp_files = []
    
    try:
        if is_youtube_link(link):
            downloader = _download_youtube
        elif is_magnet_link(link):
            downloader = _download_torrent
        elif is_http_link(link):
            downloader = _download_http
        else:
            raise ValueError("Unsupported link type. Please provide an HTTP, YouTube, or magnet link.")

        downloaded_path = await downloader(link, progress_message)
        temp_files.append(downloaded_path)
        
        await progress_message.edit("<code>Uploading to Telegram...</code>")
        
        reply_params = ReplyParameters(message_id=message.id)
        await bot.send_document(
            chat_id=message.chat_id,
            document=downloaded_path,
            caption=f"Downloaded: <code>{os.path.basename(downloaded_path)}</code>",
            reply_parameters=reply_params
        )
        
        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not complete download.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
    finally:
        # Clean up all temporary files and folders
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        os.makedirs(TEMP_DIR, exist_ok=True)
