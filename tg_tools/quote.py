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

CANVAS_BG_COLOR = (0, 0, 0, 255)
BUBBLE_COLOR = (24, 35, 43, 255)
TEXT_COLOR = (255, 255, 255, 255)

PFP_SIZE = 64
PADDING = 15
CANVAS_PADDING = 10
SUPERSAMPLE_FACTOR = 4
ERROR_VISIBLE_DURATION = 8

if not os.path.exists(FONT_REGULAR_PATH) or not os.path.exists(FONT_BOLD_PATH):
    FONT_REGULAR_PATH, FONT_BOLD_PATH = None, None

def get_color_from_id(user_id: int) -> tuple[int, int, int, int]:
    hue = (user_id % 360) / 360.0
    saturation, lightness = 0.8, 0.6
    rgb_float = colorsys.hls_to_rgb(hue, lightness, saturation)
    rgb_int = tuple(int(c * 255) for c in rgb_float)
    return (*rgb_int, 255)

def create_quote_image(pfp_path: str | None, name: str, text: str, name_color: tuple) -> str:
    ss = SUPERSAMPLE_FACTOR
    pfp_size_ss, padding_ss, canvas_padding_ss = PFP_SIZE * ss, PADDING * ss, CANVAS_PADDING * ss
    
    try:
        name_font = ImageFont.truetype(FONT_BOLD_PATH, 24 * ss)
        text_font = ImageFont.truetype(FONT_REGULAR_PATH, 24 * ss)
    except Exception:
        name_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    NAME_TEXT_GAP = 5 * ss

    temp_draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
    lines = textwrap.wrap(text, width=35)
    wrapped_text = "\n".join(lines)
    
    name_bbox = temp_draw.textbbox((0, 0), name, font=name_font)
    text_bbox = temp_draw.multiline_textbbox((0, 0), wrapped_text, font=text_font)

    name_width, name_height = name_bbox[2] - name_bbox[0], name_bbox[3] - name_bbox[1]
    text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
    
    bubble_width = max(name_width, text_width) + padding_ss * 2
    bubble_height = name_height + text_height + padding_ss * 2 + (NAME_TEXT_GAP if text else 0)
    
    content_width = pfp_size_ss + padding_ss + bubble_width
    content_height = max(pfp_size_ss, bubble_height)
    
    final_width_ss = content_width + canvas_padding_ss * 2
    final_height_ss = content_height + canvas_padding_ss * 2
    
    large_image = Image.new('RGBA', (int(final_width_ss), int(final_height_ss)), CANVAS_BG_COLOR)
    draw = ImageDraw.Draw(large_image)

    pfp_x, pfp_y = canvas_padding_ss, canvas_padding_ss
    bubble_x0, bubble_y0 = pfp_x + pfp_size_ss + padding_ss, pfp_y
    
    draw.rounded_rectangle((bubble_x0, bubble_y0, bubble_x0 + bubble_width, bubble_y0 + bubble_height), radius=20 * ss, fill=BUBBLE_COLOR)
    
    text_x = bubble_x0 + padding_ss
    text_y = bubble_y0 + (padding_ss * 0.8)

    draw.text((text_x, text_y), name, font=name_font, fill=name_color)
    draw.text((text_x, text_y + name_height + NAME_TEXT_GAP), wrapped_text, font=text_font, fill=TEXT_COLOR)
    
    if pfp_path:
        try:
            with Image.open(pfp_path).convert("RGBA") as pfp_image:
                pfp_image = pfp_image.resize((pfp_size_ss, pfp_size_ss), Image.Resampling.LANCZOS)
                mask = Image.new('L', pfp_image.size, 0)
                ImageDraw.Draw(mask).ellipse((0, 0, pfp_size_ss, pfp_size_ss), fill=255)
                large_image.paste(pfp_image, (pfp_x, pfp_y), mask)
        except Exception:
            pass

    final_width = int(final_width_ss / ss)
    final_height = int(final_height_ss / ss)
    final_image = large_image.resize((final_width, final_height), Image.Resampling.LANCZOS)

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
    
    progress_message = await message.reply("Creating image...")
    
    pfp_path, file_path = None, ""
    temp_files = []

    try:
        if author_user.photo:
            pfp_path = await bot.download_media(
                author_user.photo.big_file_id, 
                file_name=os.path.join(TEMP_DIR, f"pfp_{author_user.id}.jpg")
            )
        else:
            pfp_path = await asyncio.to_thread(create_stock_pfp, author_name, author_user.id)
        
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

def create_stock_pfp(name: str, user_id: int) -> str:
    ss = SUPERSAMPLE_FACTOR
    size_ss = PFP_SIZE * ss
    font_size_ss = int(size_ss * 0.45)
    
    image = Image.new('RGBA', (size_ss, size_ss), (0,0,0,0))
    draw = ImageDraw.Draw(image)
    
    bg_color = get_color_from_id(user_id)
    initials = (name.split()[0][0] + (name.split()[-1][0] if len(name.split()) > 1 else "")).upper() if name else "?"
    
    draw.ellipse((0, 0, size_ss, size_ss), fill=bg_color)
    
    try:
        font = ImageFont.truetype(FONT_BOLD_PATH, font_size_ss)
    except Exception:
        font = ImageFont.load_default()

    draw.text((size_ss / 2, size_ss / 2), initials, font=font, fill=(255, 255, 255), anchor="mm")
    
    final_image = image.resize((PFP_SIZE, PFP_SIZE), Image.Resampling.LANCZOS)
    
    path = os.path.join(TEMP_DIR, f"stock_pfp_{user_id}.png")
    final_image.save(path, 'PNG')
    return path
