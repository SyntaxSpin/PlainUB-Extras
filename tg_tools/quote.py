import os
import textwrap
import html
from PIL import Image, ImageDraw, ImageFont
import asyncio
from pyrogram.types import Message

from app import BOT, bot

TEMP_DIR = "temp_stickers"
os.makedirs(TEMP_DIR, exist_ok=True)
FONT_PATH = "assets/Roboto-Regular.ttf" 
FONT_SIZE = 40
AUTHOR_FONT_SIZE = 30
IMG_WIDTH, IMG_HEIGHT = 512, 512
ERROR_VISIBLE_DURATION = 8

if not os.path.exists(FONT_PATH):
    FONT_PATH = None

def create_quote_image(text: str, author: str) -> str:
    """Creates an image with the quote and saves it as a png."""
    img = Image.new('RGBA', (IMG_WIDTH, IMG_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE) if FONT_PATH else ImageFont.load_default()
        author_font = ImageFont.truetype(FONT_PATH, AUTHOR_FONT_SIZE) if FONT_PATH else ImageFont.load_default()
    except IOError:
        font = ImageFont.load_default()
        author_font = ImageFont.load_default()

    margin = 40
    lines = []
    paragraphs = text.split('\n')
    for paragraph in paragraphs:
        wrapped_lines = textwrap.wrap(paragraph, width=20, replace_whitespace=False)
        lines.extend(wrapped_lines if wrapped_lines else [''])

    y_text = margin
    for line in lines:
        draw.text((margin, y_text), line, font=font, fill="white")
        y_text += font.getbbox(line)[3] + 10

    y_text += 20
    draw.text((margin, y_text), f"~ {author}", font=author_font, fill="yellow")

    output_path = os.path.join(TEMP_DIR, f"quote_{hash(text + author)}.png")
    img.save(output_path, 'PNG')
    return output_path


@bot.add_cmd(cmd=["q", "quote"])
async def quote_sticker_handler(bot: BOT, message: Message):
    """
    CMD: Q | QUOTE
    INFO: Creates an image from a replied message.
    """
    
    if not message.replied or not (message.replied.text or message.replied.caption):
        await message.edit("Please reply to a message with text to quote.")
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await message.delete()
        return

    text_to_quote = message.replied.text or message.replied.caption
    author = "Anonymous"
    if message.replied.from_user:
        author = message.replied.from_user.first_name
    elif message.replied.sender_chat:
        author = message.replied.sender_chat.title

    progress_message = await message.reply("Creating image... 🎨")
    
    file_path = ""
    try:
        file_path = await asyncio.to_thread(create_quote_image, text_to_quote, author)
        
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=file_path,
            caption=f"Quote by {author}",
            reply_to_message_id=message.reply_to_message_id
        )
        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not create image.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text)
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await progress_message.delete()
        try:
            await message.delete()
        except Exception:
            pass
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
