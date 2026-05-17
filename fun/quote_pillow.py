import os
import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from app import BOT, bot, Message

try:
    import cairosvg
except ImportError:
    cairosvg = None

FONT_DIR = "./fonts"
SHAPE_DIR = "./shapes"

FONTS = {
    "-m": "jbmono.ttf",
    "-sf": "cm.ttf",
    "-ssf": "google.ttf",
    "-sfi": "cmitalic.ttf"
}

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
    
    if not os.path.exists(svg_path) or not cairosvg:
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        return mask

    png_bytes = cairosvg.svg2png(url=svg_path, parent_width=size, parent_height=size)
    mask_img = Image.open(BytesIO(png_bytes)).convert("RGBA")
    return mask_img.split()[-1]

def generate_quote_image(pfp_bytes: BytesIO, author_name: str, text: str, font_flag: str = "-ssf", shape_name: str = None) -> BytesIO:
    canvas_w, canvas_h = 1024, 576
    
    pfp = Image.open(pfp_bytes)
    bg = crop_to_16_9(pfp).resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=15))
    
    enhancer = ImageEnhance.Brightness(bg)
    bg = enhancer.enhance(0.35)
    
    pfp_size = 240
    pfp_square = pfp.resize((pfp_size, pfp_size), Image.Resampling.LANCZOS)
    
    if shape_name:
        mask = get_shape_mask(shape_name, pfp_size)
    else:
        mask = Image.new("L", (pfp_size, pfp_size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, pfp_size, pfp_size), fill=255)
        
    avatar_pasted = Image.new("RGBA", (pfp_size, pfp_size))
    avatar_pasted.paste(pfp_square, (0, 0), mask=mask)
    
    avatar_x = 80
    avatar_y = (canvas_h - pfp_size) // 2
    bg.paste(avatar_pasted, (avatar_x, avatar_y), mask=avatar_pasted.split()[-1] if avatar_pasted.mode == "RGBA" else None)
    
    draw = ImageDraw.Draw(bg)
    
    font_file = FONTS.get(font_flag, "google.ttf")
    font_path = os.path.join(FONT_DIR, font_file)
    
    try:
        quote_font = ImageFont.truetype(font_path, 42)
        author_font = ImageFont.truetype(font_path, 28)
    except IOError:
        quote_font = ImageFont.load_default()
        author_font = ImageFont.load_default()
        
    text_start_x = avatar_x + pfp_size + 60
    max_text_width = canvas_w - text_start_x - 80
    
    words = text.split(' ')
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        bbox = draw.textbbox((0, 0), ' '.join(current_line), font=quote_font)
        if bbox[2] - bbox[0] > max_text_width:
            current_line.pop()
            lines.append(' '.join(current_line))
            current_line = [word]
    lines.append(' '.join(current_line))
    
    line_height = draw.textbbox((0, 0), "A", font=quote_font)[3] + 10
    total_text_height = (len(lines) * line_height) + 40
    
    start_y = (canvas_h - total_text_height) // 2
    
    for i, line in enumerate(lines):
        draw.text((text_start_x, start_y + (i * line_height)), line, font=quote_font, fill="#FFFFFF")
        
    author_y = start_y + (len(lines) * line_height) + 15
    draw.text((text_start_x, author_y), f"— {author_name}", font=author_font, fill="#FF527B")
    
    output_buffer = BytesIO()
    bg.save(output_buffer, "JPEG", quality=90)
    output_buffer.seek(0)
    return output_buffer


@bot.add_cmd(cmd=["qutimg", "qt", "qimg"])
async def quote_cmd_handler(bot: BOT, message: Message):
    """ Quoting Someone in full image options -m : Mono , -sf : serif , -ssf : sansserif , -sfi italic , --mds : with material shape \n example command : [reply] , or .qutimg options @username text  """
    text = message.text
    if not text:
        return await message.reply("Provide arguments!")

    args = text.split()
    font_flag = "-ssf"
    use_mds = False
    quote_text_list = []
    
    for arg in args[1:]:
        if arg in ["-m", "-sf", "-ssf", "-sfi"]:
            font_flag = arg
        elif arg == "--mds":
            use_mds = True
        elif arg.startswith("@"):
            continue
        else:
            quote_text_list.append(arg)
            
    quote_text = " ".join(quote_text_list)
    
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
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    
    if not target_user:
        target_user = message.from_user
        
    full_name = f"{target_user.first_name or ''} {target_user.last_name or ''}".strip()
    if not full_name:
        full_name = target_user.username or "Anonymous"
        
    status_msg = await message.reply("[1/3] Downloading target user's profile photo...")
    
    temp_pfp_path = f"temp_pfp_{target_user.id}.jpg"
    pfp_stream = BytesIO()
    
    try:
        if target_user.photo:
            await bot.download_media(target_user.photo.big_file_id, file_name=temp_pfp_path)
            if os.path.exists(temp_pfp_path):
                with open(temp_pfp_path, "rb") as f:
                    pfp_stream.write(f.read())
                pfp_stream.seek(0)
                os.remove(temp_pfp_path)
        else:
            img = Image.new('RGB', (300, 300), color='#718093')
            img.save(pfp_stream, "JPEG")
            pfp_stream.seek(0)
            
    except Exception as download_error:
        if os.path.exists(temp_pfp_path):
            os.remove(temp_pfp_path)
        return await status_msg.edit(f"Failed to fetch profile image: {str(download_error)}")

    await status_msg.edit("[2/3] Processing canvas and layout...")
    
    try:
        final_photo_stream = generate_quote_image(
            pfp_bytes=pfp_stream,
            author_name=full_name,
            text=quote_text if quote_text else "No text provided.",
            font_flag=font_flag,
            shape_name=shape_name
        )
        
        await status_msg.edit("[3/3] Sending generated quote image...")
        
        final_photo_stream.name = "quote.jpg"
        await message.reply_photo(photo=final_photo_stream)
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit(f"Generation Failed: {str(e)}")
    finally:
        if os.path.exists(temp_pfp_path):
            os.remove(temp_pfp_path)