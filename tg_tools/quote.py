import os
import textwrap
import html
from PIL import Image, ImageDraw, ImageFont
import asyncio
from pyrogram import filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message, User
import requests
import colorsys

from app import BOT, bot

QUOTLY_BOT_ID = 1031952739

TEMP_DIR = "temp_quotes"
os.makedirs(TEMP_DIR, exist_ok=True)
FONT_REGULAR_PATH = "app/modules/NotoSans-Regular.ttf" 
FONT_BOLD_PATH = "app/modules/NotoSans-Bold.ttf"
CANVAS_BG_COLOR = (0, 0, 0, 255)
BUBBLE_COLOR = (24, 35, 43, 255)
TEXT_COLOR = (255, 255, 255, 255)
PFP_SIZE, PADDING, CANVAS_PADDING, SUPERSAMPLE_FACTOR, ERROR_VISIBLE_DURATION = 64, 15, 10, 4, 8

if not os.path.exists(FONT_REGULAR_PATH) or not os.path.exists(FONT_BOLD_PATH):
    FONT_REGULAR_PATH, FONT_BOLD_PATH = None, None

def get_color_from_id(user_id: int):
    hue, sat, light = (user_id % 360) / 360.0, 0.8, 0.6
    rgb_float = colorsys.hls_to_rgb(hue, light, sat)
    return tuple(int(c * 255) for c in rgb_float) + (255,)

def create_stock_pfp(name: str, user_id: int):
    ss = SUPERSAMPLE_FACTOR
    size_ss, font_size_ss = PFP_SIZE * ss, int(PFP_SIZE * ss * 0.45)
    image = Image.new('RGBA', (size_ss, size_ss), (0,0,0,0))
    draw = ImageDraw.Draw(image)
    bg_color = get_color_from_id(user_id)
    initials = (name.split()[0][0] + (name.split()[-1][0] if len(name.split()) > 1 else "")).upper() if name else "?"
    draw.ellipse((0, 0, size_ss, size_ss), fill=bg_color)
    try: font = ImageFont.truetype(FONT_BOLD_PATH, font_size_ss)
    except: font = ImageFont.load_default()
    draw.text((size_ss / 2, size_ss / 2), initials, font=font, fill=(255, 255, 255), anchor="mm")
    final_image = image.resize((PFP_SIZE, PFP_SIZE), Image.Resampling.LANCZOS)
    path = os.path.join(TEMP_DIR, f"stock_pfp_{user_id}.png")
    final_image.save(path, 'PNG')
    return path

def create_multiquote_image(messages_data: list):
    ss = SUPERSAMPLE_FACTOR
    pfp_size_ss, padding_ss, canvas_padding_ss = PFP_SIZE * ss, PADDING * ss, CANVAS_PADDING * ss
    try:
        name_font = ImageFont.truetype(FONT_BOLD_PATH, 24 * ss)
        text_font = ImageFont.truetype(FONT_REGULAR_PATH, 24 * ss)
    except:
        name_font, text_font = ImageFont.load_default(), ImageFont.load_default()

    total_height = canvas_padding_ss
    message_elements = []
    for msg_data in messages_data:
        lines = textwrap.wrap(msg_data["text"], width=35)
        wrapped_text = "\n".join(lines)
        name_bbox = ImageDraw.Draw(Image.new('RGB',(1,1))).textbbox((0,0), msg_data["author_name"], font=name_font)
        text_bbox = ImageDraw.Draw(Image.new('RGB',(1,1))).multiline_textbbox((0,0), wrapped_text, font=text_font)
        name_h, text_h = name_bbox[3] - name_bbox[1], text_bbox[3] - text_bbox[1]
        bubble_h = name_h + text_h + padding_ss * 2 + (5 * ss if msg_data["text"] else 0)
        current_h = max(pfp_size_ss, bubble_h) + padding_ss
        message_elements.append({"wrapped_text": wrapped_text, "name_bbox": name_bbox, "height": current_h})
        total_height += current_h

    final_image = Image.new('RGBA', (int(PFP_SIZE * ss + padding_ss * 3 + max(m["name_bbox"][2] for m in message_elements)), int(total_height)), CANVAS_BG_COLOR)
    draw = ImageDraw.Draw(final_image)
    current_y = canvas_padding_ss

    for i, element in enumerate(message_elements):
        msg_data = messages_data[i]
        pfp_path = msg_data.get("pfp_path")
        
        pfp_image = None
        if pfp_path:
            try:
                pfp_image = Image.open(pfp_path).convert("RGBA").resize((pfp_size_ss, pfp_size_ss), Image.Resampling.LANCZOS)
                mask = Image.new('L', pfp_image.size, 0)
                ImageDraw.Draw(mask).ellipse((0, 0, pfp_size_ss, pfp_size_ss), fill=255)
            except: pfp_image = None
        
        bubble_x0, bubble_y0 = canvas_padding_ss + pfp_size_ss + padding_ss, current_y
        bubble_w = max(m["name_bbox"][2] for m in message_elements) + padding_ss * 2
        bubble_h = element["height"] - padding_ss
        
        draw.rounded_rectangle((bubble_x0, bubble_y0, bubble_x0 + bubble_w, bubble_y0 + bubble_h), radius=20 * ss, fill=BUBBLE_COLOR)

        text_x, text_y = bubble_x0 + padding_ss, bubble_y0 + (padding_ss * 0.8)
        draw.text((text_x, text_y), msg_data["author_name"], font=name_font, fill=msg_data["name_color"])
        draw.text((text_x, text_y + element["name_bbox"][3] + 5 * ss), element["wrapped_text"], font=text_font, fill=TEXT_COLOR)

        if pfp_image:
            final_image.paste(pfp_image, (canvas_padding_ss, int(current_y)), mask)
        
        current_y += element["height"]

    final_size = (final_image.width // ss, final_image.height // ss)
    final_image = final_image.resize(final_size, Image.Resampling.LANCZOS)
    output_path = os.path.join(TEMP_DIR, f"quote_multi.png")
    final_image.save(output_path, 'PNG')
    return output_path


async def local_quote_fallback(message: Message, progress_message: Message, messages_to_quote: list):
    """Nasza lokalna funkcja, która działa jako fallback."""
    await progress_message.edit("@QuotLyBot did not respond, using local generator...")
    
    messages_data, download_tasks, temp_files = [], [], []
    for msg in messages_to_quote:
        author_user = msg.from_user or msg.sender_chat
        if not author_user: continue
        author_name = author_user.first_name if isinstance(author_user, User) else author_user.title
        
        msg_data = {
            "author_name": author_name,
            "name_color": get_color_from_id(author_user.id),
            "text": msg.text or msg.caption or ""
        }
        
        if author_user.photo:
            task = asyncio.create_task(bot.download_media(author_user.photo.big_file_id, file_name=os.path.join(TEMP_DIR, f"pfp_{author_user.id}.jpg")))
            download_tasks.append(task)
            msg_data["pfp_task"] = task
        else:
            task = asyncio.create_task(asyncio.to_thread(create_stock_pfp, author_name, author_user.id))
            download_tasks.append(task)
            msg_data["pfp_task"] = task
            
        messages_data.append(msg_data)

    downloaded_files = await asyncio.gather(*download_tasks)
    temp_files.extend(f for f in downloaded_files if f)
    
    for i, msg_data in enumerate(messages_data):
        messages_data[i]["pfp_path"] = downloaded_files[i]

    file_path = ""
    try:
        file_path = await asyncio.to_thread(create_multiquote_image, messages_data)
        temp_files.append(file_path)
        await bot.send_photo(chat_id=message.chat.id, photo=file_path, reply_to_message_id=message.reply_to_message_id)
        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Local generator failed.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text)
        await asyncio.sleep(ERROR_VISIBLE_DURATION)
        await progress_message.delete()
        try: await message.delete()
        except: pass
    finally:
        for f in temp_files:
            if f and os.path.exists(f): os.remove(f)

@bot.add_cmd(cmd=["q", "quote"])
async def quote_sticker_handler(bot: BOT, message: Message):
    if not message.replied:
        await message.edit("Please reply to a message to quote.", del_in=ERROR_VISIBLE_DURATION)
        return

    count = 1
    if message.input and message.input.isdigit():
        count = min(int(message.input), 10)

    progress_message = await message.reply(f"Quoting {count} message(s) via @QuotLyBot...")
    
    message_ids = range(message.replied.id, message.replied.id + count)
    messages_to_quote = await bot.get_messages(message.chat.id, message_ids)
    messages_to_quote = [m for m in messages_to_quote if m]
    
    if not messages_to_quote:
        await progress_message.edit("Could not find messages to quote.", del_in=ERROR_VISIBLE_DURATION)
        try: await message.delete()
        except: pass
        return

    try:
        queue = asyncio.Queue()
        handler = bot.add_handler(MessageHandler(
            lambda _, msg: asyncio.create_task(queue.put(msg)),
            filters=filters.user(QUOTLY_BOT_ID) & filters.sticker
        ), group=-1)

        try:
            await bot.forward_messages(QUOTLY_BOT_ID, message.chat.id, [msg.id for msg in messages_to_quote])
            
            quotly_response = await asyncio.wait_for(queue.get(), timeout=15)
            
            await bot.send_sticker(
                chat_id=message.chat.id,
                sticker=quotly_response.sticker.file_id,
                reply_to_message_id=message.reply_to_message_id
            )
            await progress_message.delete()
            await message.delete()
        finally:
            bot.remove_handler(*handler)

    except (asyncio.TimeoutError, Exception):
        await local_quote_fallback(message, progress_message, messages_to_quote)
