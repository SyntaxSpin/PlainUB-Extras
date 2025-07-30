import os
import html
import asyncio
import math
import json
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from pyrogram.types import Message

from app import BOT, bot

TEMP_DIR = "temp_checkfile/"
os.makedirs(TEMP_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 8

async def run_command(command: str) -> tuple[str, str, int]:
    process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    return (stdout.decode('utf-8', 'replace').strip(), stderr.decode('utf-8', 'replace').strip(), process.returncode)

def format_bytes(size_bytes: int) -> str:
    if size_bytes == 0: return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB"); i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i); s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

async def get_probe_data(file_path: str) -> dict | None:
    try:
        command = f'ffprobe -v quiet -print_format json -show_format -show_streams "{file_path}"'
        stdout, _, code = await run_command(command)
        if code == 0 and stdout: return json.loads(stdout)
    except: pass
    return None

def get_exif_data(file_path: str) -> dict:
    try:
        with Image.open(file_path) as img:
            exif = img.getexif();
            if not exif: return {}
            exif_data = {}
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                if isinstance(value, bytes):
                    try: value = value.decode('utf-8', 'ignore')
                    except: value = str(value)
                exif_data[str(tag)] = str(value)
            return exif_data
    except: return {}

@bot.add_cmd(cmd="checkfile")
async def checkfile_handler(bot: BOT, message: Message):
    replied_msg = message.replied
    if not replied_msg or not replied_msg.media:
        await message.edit("Please reply to any media file to check it.", del_in=ERROR_VISIBLE_DURATION)
        return

    progress_message = await message.reply("<code>Downloading for deep analysis...</code>")
    
    original_path = ""
    temp_files = []
    try:
        media_object = (replied_msg.photo or replied_msg.video or replied_msg.animation or replied_msg.document or replied_msg.audio or replied_msg.voice or replied_msg.sticker)
        original_path = await bot.download_media(media_object, file_name=os.path.join(TEMP_DIR, ""))
        temp_files.append(original_path)
        
        await progress_message.edit("<code>Analyzing...</code>")
        
        # --- Building the Ultimate Report ---
        info_lines = ["<b>File Information:</b>"]
        file_name = getattr(media_object, 'file_name', os.path.basename(original_path) if original_path else 'N/A')
        info_lines.append(f"<b>  - Name:</b> <code>{html.escape(str(file_name))}</code>")
        info_lines.append(f"<b>  - Extension:</b> <code>{os.path.splitext(file_name)[1][1:].upper() if '.' in file_name else 'N/A'}</code>")
        info_lines.append(f"<b>  - MIME Type:</b> <code>{getattr(media_object, 'mime_type', 'N/A')}</code>")
        info_lines.append(f"<b>  - Size:</b> <code>{format_bytes(getattr(media_object, 'file_size', 0))}</code>")
        
        probe_data = await get_probe_data(original_path)
        if probe_data:
            info_lines.append("\n<b>Technical Details:</b>")
            
            format_section = probe_data.get("format", {})
            format_tags = format_section.get("tags", {})
            if format_tags or "duration" in format_section:
                info_lines.append("<b>  Format / Container:</b>")
                if "duration" in format_section:
                    duration = float(format_section["duration"])
                    minutes, seconds = divmod(int(duration), 60)
                    info_lines.append(f"    - Duration: <code>{minutes:02d}:{seconds:02d}</code>")
                if "creation_time" in format_tags: info_lines.append(f"    - Creation Time: <code>{format_tags['creation_time']}</code>")
                if "encoder" in format_tags: info_lines.append(f"    - Encoder/Software: <code>{html.escape(format_tags['encoder'])}</code>")
                if "title" in format_tags: info_lines.append(f"    - Title: <code>{html.escape(format_tags['title'])}</code>")

            streams = probe_data.get("streams") or []
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

            if video_stream:
                info_lines.append("<b>  Video Stream:</b>")
                info_lines.append(f"    - Resolution: <code>{video_stream.get('width')}x{video_stream.get('height')}</code>")
                info_lines.append(f"    - Codec: <code>{video_stream.get('codec_long_name', 'N/A')}</code> (<code>{video_stream.get('codec_name', 'N/A')}</code>)")
                info_lines.append(f"    - Profile: <code>{video_stream.get('profile', 'N/A')}</code>")
                info_lines.append(f"    - Pixel Format: <code>{video_stream.get('pix_fmt', 'N/A')}</code>")
                if "avg_frame_rate" in video_stream and video_stream["avg_frame_rate"] != "0/0":
                    num, den = map(int, video_stream["avg_frame_rate"].split('/')); fps = round(num / den, 2) if den != 0 else 0
                    info_lines.append(f"    - Framerate: <code>{fps} FPS</code>")
                bit_rate = int(video_stream.get('bit_rate', 0))
                if bit_rate > 0: info_lines.append(f"    - Bitrate: <code>{round(bit_rate / 1000)} kb/s</code>")

            if audio_stream:
                info_lines.append("<b>  Audio Stream:</b>")
                info_lines.append(f"    - Codec: <code>{audio_stream.get('codec_long_name', 'N/A')}</code> (<code>{audio_stream.get('codec_name', 'N/A')}</code>)")
                info_lines.append(f"    - Sample Rate: <code>{audio_stream.get('sample_rate')} Hz</code>")
                info_lines.append(f"    - Channels: <code>{audio_stream.get('channels')}</code> ({audio_stream.get('channel_layout', 'N/A')})")
                bit_rate = int(audio_stream.get('bit_rate', 0))
                if bit_rate > 0: info_lines.append(f"    - Bitrate: <code>{round(bit_rate / 1000)} kb/s</code>")
        
        exif_data = get_exif_data(original_path)
        if exif_data:
            info_lines.append("\n<b>EXIF Data:</b>")
            for tag, value in exif_data.items():
                if len(str(value)) < 70 and str(value).strip():
                    info_lines.append(f"<b>  - {tag}:</b> <code>{html.escape(value)}</code>")

        final_report = "\n".join(info_lines)
        
        await bot.send_message(message.chat.id, final_report, reply_to_message_id=replied_msg.id)
        await progress_message.delete(); await message.delete()
    except Exception as e:
        await progress_message.edit(f"<b>Error:</b> Could not check file.\n<code>{html.escape(str(e))}</code>", del_in=ERROR_VISIBLE_DURATION)
    finally:
        for f in temp_files:
            if f and os.path.exists(f): os.remove(f)
