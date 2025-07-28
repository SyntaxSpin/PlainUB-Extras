import html
import pyfiglet
from pyrogram.types import Message

from app import BOT, bot

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
        return

    # Generate the ASCII art
    try:
        ascii_text = pyfiglet.figlet_format(text_to_convert)
        
        # Format for Telegram's monospace font
        final_text = f"<pre language=ascii>{html.escape(ascii_text)}</pre>"
        
        # Check if the message is too long for Telegram
        if len(final_text) > 4096:
            await message.edit("The resulting ASCII art is too long to be sent.")
        else:
            await message.edit(final_text)

    except Exception as e:
        await message.edit(f"<b>Error:</b> Could not generate ASCII art.\n<code>{html.escape(str(e))}</code>")
