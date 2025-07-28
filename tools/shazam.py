import os
import json
import asyncio
import html
from dotenv import load_dotenv
from acrcloud.recognizer import ACRCloudRecognizer
from pyrogram.types import Message
import pathlib

from app import BOT, bot

MODULES_DIR = pathlib.Path(__file__).parent.parent
DOTENV_PATH = MODULES_DIR / ".env"

if DOTENV_PATH.is_file():
    load_dotenv(dotenv_path=DOTENV_PATH)

ACRCLOUD_CONFIG = {
    'host': os.getenv("ACR_HOST", "identify-eu-west-1.acrcloud.com"),
    'access_key': os.getenv("ACR_ACCESS_KEY"),
    'access_secret': os.getenv("ACR_ACCESS_SECRET"),
    'recognize_type': 'audio',
    'timeout': 10
}

TEMP_DIR = "temp_shazam/"
os.makedirs(TEMP_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 8

def sync_recognize_music(file_path: str) -> dict:
    if not ACRCLOUD_CONFIG['access_key'] or not ACRCLOUD_CONFIG['access_secret']:
        raise ValueError("ACRCloud API keys are not configured in app/modules/.env")
        
    recognizer = ACRCloudRecognizer(ACRCLOUD_CONFIG)
    result_json = recognizer.recognize_by_file(file_path, start_seconds=0)
    result = json.loads(result_json)
    
    if result.get("status", {}).get("code") == 0 and "metadata" in result:
        return result["metadata"]["music"][0]
    else:
        error_msg = result.get("status", {}).get("msg", "No result")
        raise ValueError(f"ACRCloud: {error_msg}")


@bot.add_cmd(cmd=["shazam", "findsong"])
async def shazam_handler(bot: BOT, message: Message):
    if not ACRCLOUD_CONFIG['access_key'] or not ACRCLOUD_CONFIG['access_secret']:
        await message.edit("<b>ACRCloud API keys are not set up.</b> Please create an <code>app/modules/.env</code> file.", del_in=ERROR_VISIBLE_DURATION)
        return

    if not message.replied or not (message.replied.audio or message.replied.voice or message.replied.video):
        await message.edit("Please reply to an audio, voice, or video message.", del_in=ERROR_VISIBLE_DURATION)
        return

    replied_msg = message.replied
    progress_message = await message.reply("<code>Downloading audio...</code>")
    
    file_path = ""
    try:
        file_path = await bot.download_media(replied_msg)
        await progress_message.edit("<code>Recognizing music...</code>")
        music_data = await asyncio.to_thread(sync_recognize_music, file_path)
        
        artist = music_data.get("artists", [{"name": "Unknown"}])[0]["name"]
        title = music_data.get("title", "Unknown Title")
        album = music_data.get("album", {}).get("name", "Unknown Album")
        
        final_text = (
            f"<b>🎵 Music Found!</b>\n\n"
            f"<b>• Artist:</b> <code>{html.escape(artist)}</code>\n"
            f"<b>• Title:</b> <code>{html.escape(title)}</code>\n"
            f"<b>• Album:</b> <code>{html.escape(album)}</code>"
        )
        
        await progress_message.edit(final_text)
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not recognize music.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
        try: await message.delete()
        except: pass
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
