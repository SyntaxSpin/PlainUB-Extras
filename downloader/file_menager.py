import os
import html
import asyncio
import shutil
import math
from pyrogram.types import Message

from app import BOT, bot

UBOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOWNLOADS_DIR = os.path.join(UBOT_DIR, "downloads/")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 8

def format_bytes(size_bytes: int) -> str:
    if size_bytes == 0: return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

async def handle_error_and_cleanup(message: Message, error_text: str):
    """Sends an error message, waits, and deletes both messages together."""
    error_msg = await message.reply(error_text)
    await asyncio.sleep(ERROR_VISIBLE_DURATION)
    try:
        await error_msg.delete()
        await message.delete()
    except:
        pass

@bot.add_cmd(cmd="listfiles")
async def listfiles_handler(bot: BOT, message: Message):
    """
    CMD: LISTFILES
    INFO: Lists all files in the downloads directory.
    USAGE:
        .listfiles
    """
    try:
        files = os.listdir(DOWNLOADS_DIR)
        file_list = []
        if files:
            for f in sorted(files):
                file_path = os.path.join(DOWNLOADS_DIR, f)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    file_list.append(f"<code>- {html.escape(f)}</code>  <i>({format_bytes(file_size)})</i>")

        if not file_list:
            await handle_error_and_cleanup(message, "Your downloads folder is empty.")
            return

        final_report = "<b>Downloaded Files:</b>\n" + "\n".join(file_list)
        await message.reply(final_report)
        await message.delete()
    except Exception as e:
        await handle_error_and_cleanup(message, f"<b>Error:</b> Could not list files.\n<code>{html.escape(str(e))}</code>")

@bot.add_cmd(cmd="send")
async def send_handler(bot: BOT, message: Message):
    """
    CMD: SEND
    INFO: Sends a file from the downloads directory.
    USAGE:
        .send [filename]
    """
    if not message.input:
        await handle_error_and_cleanup(message, "<b>Usage:</b> .send [filename]")
        return

    filename = message.input.strip()
    file_path = os.path.join(DOWNLOADS_DIR, filename)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        await handle_error_and_cleanup(message, f"File <code>{html.escape(filename)}</code> not found in downloads.")
        return

    progress = await message.reply(f"<code>Uploading {html.escape(filename)}...</code>")
    try:
        await bot.send_document(
            chat_id=message.chat.id,
            document=file_path,
            reply_to_message_id=message.id
        )
        await progress.delete()
        await message.delete()
    except Exception as e:
        await progress.delete()
        await handle_error_and_cleanup(message, f"<b>Error:</b> Could not send file.\n<code>{html.escape(str(e))}</code>")

@bot.add_cmd(cmd="delete")
async def delete_handler(bot: BOT, message: Message):
    """
    CMD: DELETE
    INFO: Deletes a file (or all files) from the downloads directory.
    USAGE:
        .delete [filename]
        .delete all
    """
    if not message.input:
        await handle_error_and_cleanup(message, "<b>Usage:</b> .delete [filename] OR .delete all")
        return

    target = message.input.strip()

    if target.lower() == "all":
        try:
            shutil.rmtree(DOWNLOADS_DIR)
            os.makedirs(DOWNLOADS_DIR)
            await message.reply("✅ All files in downloads folder have been deleted.")
            await message.delete()
        except Exception as e:
            await handle_error_and_cleanup(message, f"<b>Error:</b> Could not clear downloads folder.\n<code>{html.escape(str(e))}</code>")
        return

    file_path = os.path.join(DOWNLOADS_DIR, target)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        await handle_error_and_cleanup(message, f"File <code>{html.escape(target)}</code> not found.")
        return

    try:
        os.remove(file_path)
        await message.reply(f"✅ File <code>{html.escape(target)}</code> has been deleted.")
        await message.delete()
    except OSError as e:
        await handle_error_and_cleanup(message, f"<b>OS Error:</b> Could not delete file.\n<code>{html.escape(str(e))}</code>")
