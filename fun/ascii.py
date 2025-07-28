import html
from pyfiglet import figlet_format
import asyncio
from pyrogram.types import Message

from app import BOT, bot

ERROR_VISIBLE_DURATION = 8

@bot.add_cmd(cmd="ascii")
async def ascii_handler(bot: BOT, message: Message):
    """
    CMD: ASCII
    INFO: Converts text to ASCII art.
    """
    
    text_to_convert = message.input
    if not text_to_convert:
        await message.edit("Usage: `.ascii <your text>`")
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await message.delete()
        return

    if len(text_to_convert) > 20:
        await message.edit("Text is too long! Please keep it under 20 characters.")
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await message.delete()
        return

    progress_message = await message.reply("Generating ASCII...")

    try:
        ascii_art = figlet_format(text_to_convert, font='standard')
        final_text = f"<code>{ascii_art}</code>"

        await progress_message.edit(final_text)
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not generate ASCII art.\n<code>{safe_escape(str(e))}</code>"
        await progress_message.edit(error_text)
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await progress_message.delete()
        try:
            await message.delete()
        except Exception:
            pass
