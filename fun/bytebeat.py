import os
import asyncio
import time
import numpy as np
from scipy.io.wavfile import write as write_wav
from pyrogram.types import Message, ReplyParameters

from app import BOT, bot

TEMP_DIR = "temp_bytebeat/"
os.makedirs(TEMP_DIR, exist_ok=True)

async def generate_bytebeat_audio(formula: str, duration_s: int, samplerate: int = 8000) -> str:
    t = np.arange(0, duration_s * samplerate)
    
    safe_globals = {
        '__builtins__': None,
        't': t,
    }
    
    try:
        audio_data = eval(formula, safe_globals) % 256
    except Exception as e:
        raise ValueError(f"Invalid or unsafe formula: {e}")

    wav_data = audio_data.astype(np.uint8)
    
    output_path = os.path.join(TEMP_DIR, f"bytebeat_{int(time.time())}.wav")
    await asyncio.to_thread(write_wav, output_path, samplerate, wav_data)
    
    return output_path


@bot.add_cmd(cmd="bytebeat")
async def bytebeat_handler(bot: BOT, message: Message):
    if not message.input:
        await message.reply(
            "**Usage:** `.bytebeat [duration] [formula]`\n\n"
            "**Example:**\n"
            "`.bytebeat 10 (t*5&t>>7)|(t*3&t>>10)`",
            del_in=15
        )
        return

    parts = message.input.split(maxsplit=1)
    
    try:
        if len(parts) < 2:
            raise ValueError("Both duration and formula are required.")
            
        duration = int(parts[0])
        formula = parts[1]
        
        if not (0 < duration <= 60):
            raise ValueError("Duration must be between 1 and 60 seconds.")
            
    except ValueError as e:
        await message.reply(f"**Invalid input:** {e}", del_in=10)
        return

    progress_msg = await message.reply(f"`Generating bytebeat for...`")
    
    output_path = None
    try:
        output_path = await generate_bytebeat_audio(formula, duration)
        
        await bot.send_audio(
            chat_id=message.chat.id,
            audio=output_path,
            caption=f"Bytebeat formula: `{formula}`",
            reply_parameters=ReplyParameters(message_id=message.id)
        )
        
        await progress_msg.delete()
        await message.delete()

    except Exception as e:
        await progress_msg.edit(f"**Error:** ```{e}```", del_in=15)
    finally:
        if output_path and os.path.exists(output_path):
            os.remove(output_path)
