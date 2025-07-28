import cowsay
import html
from pyrogram.types import Message

from app import BOT, bot

def safe_escape(text: str) -> str:
    escaped_text = html.escape(str(text))
    return escaped_text.replace("&#x27;", "’")

@bot.add_cmd(cmd="cowsay")
async def cowsay_handler(bot: BOT, message: Message):
    """
    CMD: COWSAY
    INFO: A talking cow in your chat.
    USAGE: .cowsay [text] or reply to a message.
    """
    
    text_to_say = ""
    if message.input:
        text_to_say = message.input
    elif message.replied and message.replied.text:
        text_to_say = message.replied.text
    else:
        await message.edit("What should the cow say? Provide text or reply to a message.", del_in=8)
        return

    cow_text = cowsay.cow(text_to_say)
    final_text = f"<pre language=cowsay>{safe_escape(cow_text)}</pre>"

    await message.edit(final_text)
