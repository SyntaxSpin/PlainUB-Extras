import os
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

def generate_quote_image(pfp_path: str, author_name: str, text: str, font_flag: str = "-ssf", shape_name: str = None) -> str:
    canvas_w, canvas_h = 1024, 576
    output_path = "quote_output.jpg"
    
    pfp = Image.open(pfp_path)
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
    
    font_file = FONTS.get(font_flag, "GoogleSans-Bold.ttf")
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
    
    bg.save(output_path, "JPEG", quality=95)
    return output_path


@bot.add_cmd(cmd="qutimg")
async def quote_cmd_handler(bot: BOT, message: Message):
    text = message.text
    if not text:
        return await message.reply("Provide arguments!")

    args = text.split()
    font_flag = "-ssf"
    shape_name = None
    quote_text_list = []
    
    iterator = iter(args[1:])
    for arg in iterator:
        if arg in ["-m", "-sf", "-ssf", "-sfi"]:
            font_flag = arg
        elif arg == "--mds":
            try:
                shape_name = next(iterator)
            except StopIteration:
                shape_name = "circle"
        elif arg.startswith("@"):
            continue
        else:
            quote_text_list.append(arg)
            
    quote_text = " ".join(quote_text_list)
    target_user = None
    
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    
    if not target_user:
        target_user = message.from_user
        
    full_name = f"{target_user.first_name or ''} {target_user.last_name or ''}".strip()
    if not full_name:
        full_name = target_user.username or "Anonymous"
        
    pfp_path = "target_pfp.jpg"
    if target_user.photo:
        await bot.download_media(target_user.photo.big_file_id, file_name=pfp_path)
    else:
        img = Image.new('RGB', (500, 500), color='#718093')
        img.save(pfp_path)

    status_msg = await message.reply("Generating Image Quote...")
    
    try:
        generated_img = generate_quote_image(
            pfp_path=pfp_path,
            author_name=full_name,
            text=quote_text if quote_text else "No text provided.",
            font_flag=font_flag,
            shape_name=shape_name
        )
        
        if os.path.exists(generated_img):
            with open(generated_img, "rb") as photo_file:
                await message.reply_photo(photo=photo_file)
            await status_msg.delete()
        else:
            await status_msg.edit("Failed to locate the generated image asset.")
        
    except Exception as e:
        await status_msg.edit(f"Error: {str(e)}")
        
    finally:
        if os.path.exists(pfp_path): 
            os.remove(pfp_path)
        if 'generated_img' in locals() and os.path.exists(generated_img): 
            os.remove(generated_img)