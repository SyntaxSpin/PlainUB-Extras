import os
import html
import asyncio
import random
import shutil
from pyrogram.types import Message

from app import BOT, bot

TEMP_DIR = "temp_corrupt/"
os.makedirs(TEMP_DIR, exist_ok=True)

def corrupt_file_sync(input_path: str) -> str:
    base, ext = os.path.splitext(os.path.basename(input_path))
    output_path = os.path.join(TEMP_DIR, f"{base}_corrupted{ext}")
    shutil.copy(input_path, output_path)
    
    try:
        with open(output_path, "rb+") as f:
            file_size = os.path.getsize(output_path)
            if file_size < 5000:
                return output_path

            start_pos = random.randint(1024, 4096)
            
            corruption_size = random.randint(4096, 16384)

            if start_pos + corruption_size > file_size:
                corruption_size = file_size - start_pos -1

            if corruption_size > 0:
                f.seek(start_pos)
                random_data = os.urandom(corruption_size)
                f.write(random_data)
                    
    except Exception as e:
        raise IOError(f"Failed to corrupt file: {e}")
        
    return output_path

@bot.add_cmd(cmd="corrupt")
async def corrupt_handler(bot: BOT, message: Message):
    """
    CMD: CORRUPT
    INFO: Corrupts a replied-to file by overwriting random bytes.
    USAGE:
        .corrupt (in reply to any media or file)
    """
    replied_msg = message.replied
    
    has_media = (
        replied_msg and (
            replied_msg.document or replied_msg.photo or replied_msg.video or
            replied_msg.audio or replied_msg.voice or replied_msg.animation
        )
    )
    
    if not has_media:
        await message.reply("Please reply to a media or file to corrupt it.", del_in=8)
        return

    progress_msg = await message.reply("<code>Downloading file...</code>")
    
    original_path = None
    corrupted_path = None
    try:
        original_path = await bot.download_media(replied_msg, file_name=TEMP_DIR)
        
        await progress_msg.edit("<code>Corrupting file...</code>")
        
        corrupted_path = await asyncio.to_thread(corrupt_file_sync, original_path)
        
        await progress_msg.edit("<code>Uploading file...</code>")

        await bot.send_document(
            chat_id=message.chat.id,
            document=corrupted_path,
            caption="Here is your file 💀.",
            reply_to_message_id=replied_msg.id
        )
        
        await progress_msg.delete()
        await message.delete()

    except Exception as e:
        await progress_msg.edit(f"<b>Error:</b> <code>{html.escape(str(e))}</code>", del_in=10)
    finally:
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        os.makedirs(TEMP_DIR, exist_ok=True)
