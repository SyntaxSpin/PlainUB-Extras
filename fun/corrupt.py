import os
import html
import asyncio
import random
import shutil
from pyrogram.types import Message

from app import BOT, bot

TEMP_DIR = "temp_corrupt/"
os.makedirs(TEMP_DIR, exist_ok=True)

TEXT_EXTENSIONS = {
    '.txt', '.py', '.json', '.xml', '.html', '.css', '.js', '.md', '.csv', 
    '.log', '.ini', '.conf', '.cfg', '.sh', '.bat', '.yaml', '.yml'
}

def corrupt_file_sync(input_path: str) -> str:
    """Inteligentnie uszkadza plik w zależności od tego, czy jest tekstowy, czy binarny."""
    _, ext = os.path.splitext(os.path.basename(input_path))
    
    if ext.lower() in TEXT_EXTENSIONS:
        try:
            with open(input_path, "r+", encoding='utf-8', errors='ignore') as f:
                first_line = f.readline()
                file_size = os.path.getsize(input_path)
                
                bytes_to_destroy = file_size - len(first_line.encode('utf-8', 'ignore'))
                if bytes_to_destroy <= 0:
                    return input_path

                random_garbage_bytes = os.urandom(bytes_to_destroy)
                garbage_text = random_garbage_bytes.decode('utf-8', errors='replace')
                
                f.seek(0)
                f.truncate()
                f.write(first_line + garbage_text)
        except Exception as e:
            raise IOError(f"Failed to corrupt text file: {e}")
    else:
        try:
            with open(input_path, "rb+") as f:
                file_size = os.path.getsize(input_path)
                header_size = 512
                
                if file_size <= header_size:
                    return input_path

                f.seek(header_size)
                bytes_to_destroy = file_size - header_size
                
                chunk_size = 4096
                written_bytes = 0
                while written_bytes < bytes_to_destroy:
                    bytes_to_write = min(chunk_size, bytes_to_destroy - written_bytes)
                    random_data = os.urandom(bytes_to_write)
                    f.write(random_data)
                    written_bytes += bytes_to_write
        except Exception as e:
            raise IOError(f"Failed to corrupt binary file: {e}")
            
    return input_path

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
