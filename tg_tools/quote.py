import os
import textwrap
import html
from PIL import Image, ImageDraw, ImageFont
import asyncio
from pyrogram.types import Message, User
import requests
import colorsys

from app import BOT, bot

TEMP_DIR = "temp_quotes"
os.makedirs(TEMP_DIR, exist_ok=True)

FONT_REGULAR_PATH = "app/modules/NotoSans-Regular.ttf" 
FONT_BOLD_PATH = "app/modules/NotoSans-Bold.ttf"

BUBBLE_COLOR = (24, 35, 43, 220)
TEXT_COLOR = (255, 255, 255, 255)

PFP_SIZE = 64
PADDING = 15
CANVAS_PADDING = 10
ERROR_VISIBLE_DURATION = 8

if not os.path.exists(FONT_REGULAR_PATH) or not os.path.exists(FONT_BOLD_PATH):
    FONT_REGULAR_PATH, FONT_BOLD_PATH = None, None

def get_color_from_id(user_id: int) -> tuple[int, int, int, int]:
    hue = (user_id % 360) / 360.0
    saturation, lightness = 0.8, 0.6
    rgb_float = colorsys.hls_to_rgb(hue, lightness, saturation)
    rgb_int = tuple(int(c * 255) for c in rgb_float)
    return (*rgb_int, 255)

def sanitize_text_for_font(text: str, font: ImageFont.FreeTypeFont) -> str:
    """Bardziej niezawodna funkcja do czyszczenia tekstu."""
    sanitized_text = ""
    for char in text:
        if font.getmask(char).getbbox() is not None:
            sanitized_text += char
        else:
            sanitized_text += "□"
    return sanitized_text

def create_quote_image(pfp_path: str | None, name: str, text: str, name_color: tuple) -> str:
    try:
        name_font = ImageFont.truetype(FONT_BOLD_PATH, 24)
        text_font = ImageFont.truetype(FONT_REGULAR_PATH, 24)
    except Exception:
        name_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    sanitized_name = sanitize_text_for_font(name, name_font)
    
    temp_draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
    
    lines = textwrap.wrap(text, width=35)
    wrapped_text = "\n".join(lines)
    
    name_bbox = temp_draw.textbbox((0, 0), sanitized_name, font=name_font)
    text_bbox = temp_draw.multiline_textbbox((0, 0), wrapped_text, font=text_font)

    name_width, name_height = name_bbox[2] - name_bbox[0], name_bbox[3] - name_bbox[1]
    text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
    
    bubble_width = max(name_width, text_width) + PADDING * 2
    bubble_height = name_height + text_height + PADDING * 2 + (10 if text else 0)
    
    content_width = PFP_SIZE + PADDING + bubble_width
    content_height = max(PFP_SIZE, bubble_height)
    
    final_width = content_width + CANVAS_PADDING * 2
    final_height = content_height + CANVAS_PADDING * 2
    
    final_image = Image.new('RGBA', (int(final_width), int(final_height)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(final_image)

    pfp_x, pfp_y = CANVAS_PADDING, CANVAS_PADDING
    bubble_x0, bubble_y0 = pfp_x + PFP_SIZE + PADDING, pfp_y
    
    draw.rounded_rectangle((bubble_x0, bubble_y0, bubble_x0 + bubble_width, bubble_y0 + bubble_height), radius=20, fill=BUBBLE_COLOR)
    
    text_x = bubble_x0 + PADDING
    text_y = bubble_y0 + PADDING
    draw.text((text_x, text_y), sanitized_name, font=name_font, fill=name_color)
    draw.text((text_x, text_y + name_height + 10), wrapped_text, font=text_font, fill=TEXT_COLOR)
    
    if pfp_path:
        try:
            with Image.open(pfp_path).convert("RGBA") as pfp_image:
                pfp_image = pfp_image.resize((PFP_SIZE, PFP_SIZE), Image.Resampling.LANCZOS)
                mask = Image.new('L', (PFP_SIZE, PFP_SIZE), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, PFP_SIZE, PFP_SIZE), fill=255)
                final_image.paste(pfp_image, (pfp_x, pfp_y), mask)
        except Exception:
            pass

    output_path = os.path.join(TEMP_DIR, f"quote_{hash(text + name)}.png")
    final_image.save(output_path, 'PNG')
    return output_path


@bot.add_cmd(cmd=["q", "quote"])
async def quote_sticker_handler(bot: BOT, message: Message):
    replied_msg = message.replied
    if not replied_msg or not (replied_msg.text or replied_msg.caption):
        await message.edit("Please reply to a message with text to quote.", del_in=ERROR_VISIBLE_DURATION)
        return

    text_to_quote = replied_msg.text or replied_msg.caption
    author_user = replied_msg.from_user or replied_msg.sender_chat
    
    if not author_user:
        await message.edit("Cannot quote an anonymous admin.", del_in=ERROR_VISIBLE_DURATION)
        return

    author_name = author_user.first_name if isinstance(author_user, User) else author_user.title
    
    progress_message = await message.reply("Creating image... 🎨")
    
    pfp_path, file_path = None, ""
    temp_files = []

    try:
        if author_user.photo:
            pfp_path = await bot.download_media(
                author_user.photo.big_file_id, 
                file_name=os.path.join(TEMP_DIR, f"pfp_{author_user.id}.jpg")
            )
            if pfp_path:
                temp_files.append(pfp_path)

        author_color = get_color_from_id(author_user.id)
        
        file_path = await asyncio.to_thread(
            create_quote_image, 
            pfp_path, author_name, text_to_quote, author_color
        )
        temp_files.append(file_path)
        
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=file_path,
            reply_to_message_id=replied_msg.id
        )
        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not create image.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text)
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await progress_message.delete()
        try: await message.delete()
        except: pass
    finally:
        for f in temp_files:
            if f and os.path.exists(f):
                os.remove(f)
