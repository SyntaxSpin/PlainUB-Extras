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

FONT_REGULAR_PATH = "app/modules/Roboto-Regular.ttf" 
FONT_BOLD_PATH = "app/modules/Roboto-Bold.ttf"

BUBBLE_COLOR = (24, 35, 43, 220)
TEXT_COLOR = (255, 255, 255, 255)

IMG_WIDTH = 512
PFP_SIZE = 64
PADDING = 20
ERROR_VISIBLE_DURATION = 8

if not os.path.exists(FONT_REGULAR_PATH) or not os.path.exists(FONT_BOLD_PATH):
    FONT_REGULAR_PATH, FONT_BOLD_PATH = None, None

def get_color_from_id(user_id: int) -> tuple[int, int, int, int]:
    hue = (user_id % 360) / 360.0
    saturation, lightness = 0.9, 0.65
    rgb_float = colorsys.hls_to_rgb(hue, lightness, saturation)
    rgb_int = tuple(int(c * 255) for c in rgb_float)
    return (*rgb_int, 255)

async def sync_download_media(file_id: str, file_type: str) -> str | None:
    try:
        file = await bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{bot.bot_token}/{file.file_path}"
        response = requests.get(url)
        response.raise_for_status()
        
        ext = {"pfp": "jpg", "photo": "jpg", "sticker": "webp"}[file_type]
        media_path = os.path.join(TEMP_DIR, f"{file_id}.{ext}")
        with open(media_path, "wb") as f:
            f.write(response.content)
        return media_path
    except Exception:
        return None

def create_multiquote_image(messages_data: list) -> str:
    """Creates an image from a list of message data."""
    
    try:
        name_font = ImageFont.truetype(FONT_BOLD_PATH, 24)
        text_font = ImageFont.truetype(FONT_REGULAR_PATH, 24)
    except Exception:
        name_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    total_height = PADDING
    message_elements = []

    for msg_data in messages_data:
        pfp_path = msg_data.get("pfp_path")
        media_path = msg_data.get("media_path")
        author_name = msg_data["author_name"]
        text = msg_data.get("text", "")
        name_color = msg_data["name_color"]

        current_height = 0
        
        lines = textwrap.wrap(text, width=32)
        wrapped_text = "\n".join(lines)
        name_bbox = name_font.getbbox(author_name)
        text_bbox = text_font.getbbox(wrapped_text, anchor='lt')

        bubble_height = (name_bbox[3] + 10) + (text_bbox[3] - text_bbox[1]) + PADDING * 2 if text else name_bbox[3] + PADDING
        
        media_height = 0
        media_image = None
        if media_path:
            try:
                media_image = Image.open(media_path)
                w, h = media_image.size
                ratio = h / w
                new_w = IMG_WIDTH - (PFP_SIZE + PADDING * 2)
                new_h = int(new_w * ratio)
                media_image = media_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
                media_height = new_h + PADDING
            except Exception:
                media_image = None
        
        bubble_height += media_height
        current_height = max(PFP_SIZE + PADDING, bubble_height)
        
        message_elements.append({
            "pfp_path": pfp_path, "media_image": media_image, "media_height": media_height,
            "author_name": author_name, "wrapped_text": wrapped_text, "name_color": name_color,
            "height": current_height, "name_bbox": name_bbox, "text_bbox": text_bbox
        })
        total_height += current_height

    final_image = Image.new('RGBA', (IMG_WIDTH, total_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(final_image)
    current_y = PADDING

    for element in message_elements:
        pfp_image = None
        if element["pfp_path"]:
            try:
                pfp_image = Image.open(element["pfp_path"]).convert("RGBA")
                pfp_image = pfp_image.resize((PFP_SIZE, PFP_SIZE), Image.Resampling.LANCZOS)
                mask = Image.new('L', (PFP_SIZE, PFP_SIZE), 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.ellipse((0, 0, PFP_SIZE, PFP_SIZE), fill=255)
            except Exception:
                pfp_image = None
        
        bubble_x0, bubble_y0 = PFP_SIZE + PADDING, current_y
        bubble_width = IMG_WIDTH - (PFP_SIZE + PADDING * 2)
        bubble_height = element["height"] - PADDING
        
        draw.rounded_rectangle((bubble_x0, bubble_y0, bubble_x0 + bubble_width, bubble_y0 + bubble_height), radius=20, fill=BUBBLE_COLOR)

        text_x, text_y = bubble_x0 + PADDING, bubble_y0 + PADDING
        draw.text((text_x, text_y), element["author_name"], font=name_font, fill=element["name_color"])
        
        media_y_offset = 0
        if element["media_image"]:
            media_y_offset = element["media_height"]
            final_image.paste(element["media_image"], (int(text_x), int(text_y + element["name_bbox"][3] + 10)))

        draw.text((text_x, text_y + element["name_bbox"][3] + 10 + media_y_offset), element["wrapped_text"], font=text_font, fill=TEXT_COLOR, anchor='lt')
        
        if pfp_image:
            final_image.paste(pfp_image, (PADDING // 2, int(current_y)), mask)
        
        current_y += element["height"]

    output_path = os.path.join(TEMP_DIR, f"quote_{hash(''.join(m['author_name'] for m in messages_data))}.png")
    final_image.save(output_path, 'PNG')
    return output_path


@bot.add_cmd(cmd=["q", "quote"])
async def quote_sticker_handler(bot: BOT, message: Message):
    if not message.replied:
        await message.edit("Please reply to a message to quote.", del_in=ERROR_VISIBLE_DURATION)
        return

    count = 1
    if message.input and message.input.isdigit():
        count = min(int(message.input), 10)

    progress_message = await message.reply(f"<i>Quoting {count} message(s)...</i> 🎨")
    
    messages_to_quote_ids = range(message.replied.id, message.replied.id + count)
    messages = await bot.get_messages(message.chat.id, messages_to_quote_ids)
    
    messages_data = []
    download_tasks = []
    temp_files = []

    for msg in messages:
        if not msg: continue
        
        author_user = msg.from_user or msg.sender_chat
        if not author_user: continue

        author_name = author_user.first_name if isinstance(author_user, User) else author_user.title
        author_id = author_user.id
        
        msg_data = {
            "author_name": author_name,
            "name_color": get_color_from_id(author_id),
            "text": msg.text or msg.caption or ""
        }
        
        pfp_file_id = author_user.photo.big_file_id if author_user.photo else None
        if pfp_file_id:
            download_tasks.append(asyncio.create_task(sync_download_media(pfp_file_id, "pfp")))
            msg_data["pfp_task_index"] = len(download_tasks) - 1
        
        media_file_id, media_type = None, None
        if msg.photo:
            media_file_id, media_type = msg.photo.file_id, "photo"
        elif msg.sticker:
            media_file_id, media_type = msg.sticker.file_id, "sticker"
        
        if media_file_id:
            download_tasks.append(asyncio.create_task(sync_download_media(media_file_id, media_type)))
            msg_data["media_task_index"] = len(download_tasks) - 1
            
        messages_data.append(msg_data)

    downloaded_files = await asyncio.gather(*download_tasks)
    temp_files.extend(f for f in downloaded_files if f)

    for i, msg_data in enumerate(messages_data):
        if "pfp_task_index" in msg_data:
            messages_data[i]["pfp_path"] = downloaded_files[msg_data["pfp_task_index"]]
        if "media_task_index" in msg_data:
            messages_data[i]["media_path"] = downloaded_files[msg_data["media_task_index"]]

    file_path = ""
    try:
        if not messages_data:
            raise ValueError("Could not find any valid messages to quote.")

        file_path = await asyncio.to_thread(create_multiquote_image, messages_data)
        
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=file_path,
            reply_to_message_id=message.reply_to_message_id
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
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
