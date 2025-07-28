import cowsay
import html
import asyncio
from pyrogram.types import Message

from app import BOT, bot

ERROR_VISIBLE_DURATION = 8

@bot.add_cmd(cmd="cowsay")
async def cowsay_handler(bot: BOT, message: Message):
    """
    CMD: COWSAY
    INFO: A talking cow in your chat.
    """
    
    text_to_say = message.input or "Mooooo!"
    
    if len(text_to_say) > 100:
        text_to_say = text_to_say[:100] + "..."

    cow_output = cowsay.get_output_string('cow', text_to_say)
    final_text = f"<code>{cow_output}</code>"
    
    await message.reply(final_text)
    await message.delete()
