import html
import pyfiglet
import asyncio
from pyrogram.types import Message

from app import BOT, bot

ERROR_VISIBLE_DURATION = 8

def safe_escape(text: str) -> str:
    escaped_text = html.escape(str(text))
    return escaped_text.replace("&#x27;", "’")

@bot.add_cmd(cmd="ascii")
async def ascii_handler(bot: BOT, message: Message):
    """
    CMD: ASCII
    INFO: Converts text to ASCII art.
    USAGE: .ascii [text]
    """
    
    text_to_convert = message.input
    if not text_to_convert:
        await message.edit("Please provide text to convert. Usage: `.ascii Hello`")
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await message.delete()
        return

    try:
        ascii_text = pyfiglet.figlet_format(text_to_convert)
        final_text = f"<pre language=ascii>{safe_escape(ascii_text)}</pre>"
        
        if len(final_text) > 4096:
            await message.edit("The resulting ASCII art is too long to be sent.")
            await asyncio.sleep(ERROR_VISIBLE_DURATION)
            await message.delete()
            return

        await message.reply(final_text)
        await message.delete()

    except Exception as e:
        await message.edit(f"<b>Error:</b> Could not generate ASCII art.\n<code>{safe_escape(str(e))}</code>")
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await message.delete()
