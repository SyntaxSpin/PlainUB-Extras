import os
import random
import re
import urllib.request
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from app import BOT, bot, Message

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(SCRIPT_DIR, "fonts")
SHAPE_DIR = os.path.join(SCRIPT_DIR, "shapes")

FALLBACK_URL = "https://preview.redd.it/say-something-nice-about-homelander-v0-v1c9ju2q8u3c1.jpeg?width=1080&crop=smart&auto=webp&s=267fd4178088541c481cfe25526925e4af96a497"
ROBOTO_FONT_URL = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf"

FONTS = {
    "-m": "jbmono.ttf",
    "-sf": "cm.ttf",
    "-ssf": "google.ttf",
    "-sfi": "cmitalic.ttf"
}

def clean_unicode_name(name: str) -> str:
    cleaned = re.sub(r'[^\x20-\x7E]+', '', name)
    cleaned = ' '.join(cleaned.split())
    return cleaned if cleaned.strip() else "Anonymous"

def crop_to_16_9(image: Image.Image) -> Image.Image:
    width, height = image.size
    target_ratio = 16 / 9
    
    if width / height > target_ratio:
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        return image.crop((left, 0, left + new_width, height))
    else:
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2
        return image.crop((0, top, width, top + new_height))

def get_shape_mask(shape_name: str, size: int) -> Image.Image:
    svg_path = os.path.join(SHAPE_DIR, f"{shape_name}.svg")
    
    if not os.path.exists(svg_path):
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        return mask

    try:
        import cairosvg
        png_bytes = cairosvg.svg2png(url=svg_path, parent_width=size, parent_height=size)
        mask_img = Image.open(BytesIO(png_bytes)).convert("RGBA")
        return mask_img.split()[-1].resize((size, size), Image.Resampling.NEAREST)
    except Exception:
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        return mask

def get_scalable_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        if font_path and os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
    except Exception:
        pass

    linux_system_fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    
    for path in linux_system_fallbacks:
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        except Exception:
            continue
            
    try:
        req = urllib.request.Request(ROBOTO_FONT_URL, headers={'User-Agent': 'Mozilla'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return ImageFont.truetype(BytesIO(response.read()), size)
    except Exception:
        pass
        
    return ImageFont.load_default()

def generate_quote_image(pfp_path: str, author_name: str, text: str, font_flag: str = "-ssf", shape_name: str = None) -> BytesIO:
    canvas_w, canvas_h = 1024, 576
    pfp_size = 240
    
    with Image.open(pfp_path) as pfp:
        bg = crop_to_16_9(pfp).resize((canvas_w, canvas_h), Image.Resampling.BILINEAR)
        pfp_square = pfp.resize((pfp_size, pfp_size), Image.Resampling.BILINEAR).convert("RGBA")
        
        scrim = Image.new("RGBA", bg.size, (0, 0, 0, 165))
        bg = Image.alpha_composite(bg.convert("RGBA"), scrim).convert("RGB")
        
        if shape_name:
            mask = get_shape_mask(shape_name, pfp_size)
        else:
            mask = Image.new("L", (pfp_size, pfp_size), 0)
            draw_m = ImageDraw.Draw(mask)
            draw_m.ellipse((0, 0, pfp_size, pfp_size), fill=255)
            
        avatar_pasted = Image.new("RGBA", (pfp_size, pfp_size), (0, 0, 0, 0))
        avatar_pasted.paste(pfp_square, (0, 0), mask=mask)
        
        avatar_x = 80
        avatar_y = (canvas_h - pfp_size) // 2
        
        bg.paste(avatar_pasted, (avatar_x, avatar_y), mask=mask)
        
        draw = ImageDraw.Draw(bg)
        
        font_file = FONTS.get(font_flag, "google.ttf")
        font_path = os.path.join(FONT_DIR, font_file)
        
        quote_font = get_scalable_font(font_path, 54)
        author_font = get_scalable_font(font_path, 34)
            
        text_start_x = avatar_x + pfp_size + 60
        max_text_width = canvas_w - text_start_x - 80
        
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            try:
                bbox = draw.textbbox((0, 0), ' '.join(current_line), font=quote_font)
                line_w = bbox[2] - bbox[0]
            except Exception:
                line_w = len(' '.join(current_line)) * 28
                
            if line_w > max_text_width:
                current_line.pop()
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                
        if current_line:
            lines.append(' '.join(current_line))
        
        try:
            line_height = draw.textbbox((0, 0), "A", font=quote_font)[3] + 20
        except Exception:
            line_height = 70
            
        total_text_height = (len(lines) * line_height) + 60
        start_y = (canvas_h - total_text_height) // 2
        
        for i, line in enumerate(lines):
            draw.text((text_start_x, start_y + (i * line_height)), line, font=quote_font, fill="#FFFFFF")
            
        author_y = start_y + (len(lines) * line_height) + 20
        draw.text((text_start_x, author_y), f"— {author_name}", font=author_font, fill="#FF527B")
        
        output_buffer = BytesIO()
        bg.save(output_buffer, "JPEG", quality=75, optimize=True)
        output_buffer.seek(0)
        return output_buffer

async def safe_edit_status(status_msg, message: Message, new_text: str):
    try:
        if status_msg:
            return await status_msg.edit(new_text)
    except Exception:
        pass
    try:
        return await message.reply(new_text)
    except Exception:
        return None

async def safe_delete_status(status_msg):
    try:
        if status_msg:
            await status_msg.delete()
    except Exception:
        pass


@bot.add_cmd(cmd=["qutimg", "qt", "qimg"])
async def quote_cmd_handler(bot: BOT, message: Message):
    text = message.text
    if not text:
        return await message.reply("Provide arguments!")

    args = text.split()
    font_flag = "-ssf" 
    use_mds = False
    use_reply_text = False
    target_username = None
    quote_text_list = []
    
    # Track if we have captured the primary user target yet
    user_found = False
    
    for arg in args[1:]:
        if arg in ["-m", "-sf", "-ssf", "-sfi"]:
            font_flag = arg
        elif arg == "--mds":
            use_mds = True
        elif arg == "-r":
            use_reply_text = True
        elif arg.startswith("@") and not user_found:
            target_username = arg
            user_found = True  # Lock it so any subsequent '@' words are kept as text
        else:
            quote_text_list.append(arg)
            
    quote_text = " ".join(quote_text_list)
    
    if use_reply_text and message.reply_to_message:
        replied_text = message.reply_to_message.text or message.reply_to_message.caption
        if replied_text:
            quote_text = replied_text

    shape_name = None
    if use_mds and os.path.exists(SHAPE_DIR):
        all_shapes = [
            os.path.splitext(f)[0] 
            for f in os.listdir(SHAPE_DIR) 
            if f.lower().endswith(".svg")
        ]
        if all_shapes:
            shape_name = random.choice(all_shapes)

    target_user = None
    
    if target_username:
        try:
            target_user = await bot.get_users(target_username)
        except Exception:
            pass

    if not target_user and message.reply_to_message:
        if message.reply_to_message.from_user:
            target_user = message.reply_to_message.from_user
        elif message.reply_to_message.sender_chat:
            target_user = message.reply_to_message.sender_chat

    if not target_user:
        target_user = message.from_user
        
    if hasattr(target_user, 'first_name'):
        raw_name = f"{target_user.first_name or ''} {target_user.last_name or ''}".strip()
        if not raw_name:
            raw_name = target_user.username or "Anonymous"
    else:
        raw_name = getattr(target_user, 'title', "Anonymous")
        
    full_name = clean_unicode_name(raw_name)
    status_msg = await message.reply("[1/3] Downloading target photo...")
    
    pfp_path = os.path.abspath(f"temp_pfp_{getattr(target_user, 'id', random.randint(1000,9999))}.jpg")
    pfp_exists = False
    
    try:
        photo_obj = getattr(target_user, 'photo', None)
        if photo_obj and hasattr(photo_obj, 'big_file_id'):
            downloaded = await bot.download_media(photo_obj.big_file_id, file_name=pfp_path)
            if downloaded and os.path.exists(pfp_path):
                pfp_exists = True
        
        if not pfp_exists:
            req = urllib.request.Request(
                FALLBACK_URL, 
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                img_data = response.read()
                with Image.open(BytesIO(img_data)) as remote_img:
                    remote_img.convert("RGB").save(pfp_path, "JPEG", quality=60, optimize=True)
            pfp_exists = True
            
    except Exception as download_error:
        if os.path.exists(pfp_path):
            os.remove(pfp_path)
        await safe_edit_status(status_msg, message, f"Failed to fetch profile image: {str(download_error)}")
        return

    status_msg = await safe_edit_status(status_msg, message, "[2/3] Processing layout...")
    
    try:
        final_photo_stream = generate_quote_image(
            pfp_path=pfp_path,
            author_name=full_name,
            text=quote_text if quote_text else "No text provided.",
            font_flag=font_flag,
            shape_name=shape_name
        )
        
        status_msg = await safe_edit_status(status_msg, message, "[3/3] Sending quote image...")
        
        final_photo_stream.name = "quote.jpg"
        await message.reply_photo(photo=final_photo_stream)
        await safe_delete_status(status_msg)
        
    except Exception as e:
        await safe_edit_status(status_msg, message, f"Generation Failed: {str(e)}")
    finally:
        if os.path.exists(pfp_path):
            os.remove(pfp_path)