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
            min_pos = int(file_size * 0.1)
            
            if file_size < 1000:
                corruption_count = 2
                chunk_size = 20
            else:
                corruption_count = random.randint(5, 15)
                chunk_size = random.randint(50, 250)

            for _ in range(corruption_count):
                if file_size > min_pos + chunk_size:
                    random_position = random.randint(min_pos, file_size - chunk_size)
                    f.seek(random_position)
                    
                    random_data = os.urandom(chunk_size)
                    
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
        .corrupt (in reply to a file)
    """
    replied_msg = message.replied
    
    if not replied_msg or not replied_msg.document:
        await message.reply("Please reply to a file to corrupt it.", del_in=8)
        return

    progress_msg = await message.reply("<code>Downloading file...</code>")
    
    original_path = None
    corrupted_path = None
    try:
        original_path = await bot.download_media(replied_msg, file_name=TEMP_DIR)
        
        await progress_msg.edit("<code>Corrupting file...</code>")
        
        corrupted_path = await asyncio.to_thread(corrupt_file_sync, original_path)
        
        await progress_msg.edit("<code>Uploading corrupted file...</code>")

        await bot.send_document(
            chat_id=message.chat.id,
            document=corrupted_path,
            caption="Here is your corrupted file.",
            reply_to_message_id=replied_msg.id
        )
        
        await progress_msg.delete()
        await message.delete()

    except Exception as e:
        await progress_msg.edit(f"<b>Error:</b> <code>{html.escape(str(e))}</code>", del_in=10)
    finally:
        if original_path and os.path.exists(original_path):
            os.remove(original_path)
        if corrupted_path and os.path.exists(corrupted_path):
            os.remove(corrupted_path)
