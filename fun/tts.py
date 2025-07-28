import os
import html
import asyncio
from gtts import gTTS
from pyrogram.types import Message

from app import BOT, bot

TEMP_DIR = "temp_audio"
os.makedirs(TEMP_DIR, exist_ok=True)

def sync_gtts(text: str, lang: str) -> str:
    """
    Synchronous function to generate a speech file using gTTS.
    Returns the path to the generated file.
    """
    output_path = os.path.join(TEMP_DIR, f"{hash(text)}.mp3")
    
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(output_path)
    return output_path


@bot.add_cmd(cmd="tts")
async def tts_handler(bot: BOT, message: Message):
    """
    CMD: TTS
    INFO: Converts text to speech.
    USAGE: .tts [lang] [text] or reply with .tts [lang]
    NOTE: Defaults to English (en).
    """
    
    text_to_speak = ""
    lang = "en"

    if message.replied and message.replied.text:
        text_to_speak = message.replied.text
        if message.input:
            lang = message.input.lower()
    elif message.input:
        parts = message.input.split(maxsplit=1)
        if len(parts) > 1 and len(parts[0]) == 2 and parts[0].isalpha():
            lang = parts[0].lower()
            text_to_speak = parts[1]
        else:
            text_to_speak = message.input
    else:
        await message.edit("Please provide text or reply to a message.")
        return

    if not text_to_speak.strip():
        await message.edit("The message contains no text to convert.")
        return

    await message.edit("Converting text to speech... 🎤")
    
    file_path = ""
    try:
        file_path = await asyncio.to_thread(sync_gtts, text_to_speak, lang)
        
        await bot.send_voice(
            chat_id=message.chat.id,
            voice=file_path,
            reply_to_message_id=message.reply_to_message_id or message.id
        )
        
        await message.delete()

    except Exception as e:
        await message.edit(f"<b>Error:</b> Could not generate speech.\n<code>{html.escape(str(e))}</code>")
        await asyncio.sleep(5)
        await message.delete()
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
