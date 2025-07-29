import io

try:
    import pyfiglet
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    pyfiglet = None
    Image = ImageDraw = ImageFont = None

from app import BOT, Message, bot

def draw_monospace_text(draw: ImageDraw.Draw, text: str, position: tuple, font: ImageFont.FreeTypeFont, fill: str):
    char_width = font.getbbox(" ")[2]
    line_height = font.getbbox("A")[3] + 4
    x, y = position
    for line in text.split('\n'):
        for char in line:
            draw.text((x, y), char, font=font, fill=fill)
            x += char_width
        y += line_height
        x = position[0]

@bot.add_cmd(cmd=["ascii", "figlet"])
async def ascii_cmd_img(bot: BOT, message: Message):
    """
    CMD: ASCII / FIGLET
    INFO: Generates an image with large ASCII art text.
    USAGE:
        .ascii <text>
    """
    if not pyfiglet or not Image:
        await message.edit(
            "<b>Required libraries not found.</b>\n"
            "Please install them using: <code>pip install pyfiglet Pillow</code>"
        )
        return

    if not message.input:
        await message.edit("What should I write in ASCII? Provide some text.", del_in=5)
        return

    progress_msg = await message.edit("<code>Generating art...</code>")
    text_to_render = message.input
    
    fig = pyfiglet.Figlet(font='slant')
    ascii_text = fig.renderText(text_to_render)

    font = ImageFont.load_default()
    
    lines = ascii_text.split('\n')
    longest_line = max(lines, key=len)
    char_width = font.getbbox(" ")[2]
    line_height = font.getbbox("A")[3] + 4

    img_width = int(len(longest_line) * char_width) + 40
    img_height = int(len(lines) * line_height) + 40
    img_size = (img_width, img_height)

    img = Image.new('RGB', img_size, color='black')
    draw = ImageDraw.Draw(img)
    
    draw_monospace_text(draw, ascii_text, (20, 20), font, 'white')
    
    await progress_msg.edit("<code>Uploading...</code>")
    
    with io.BytesIO() as bio:
        bio.name = 'ascii.png'
        img.save(bio, 'PNG')
        bio.seek(0)
        
        await message.reply_photo(
            photo=bio,
            caption=f"<code>.ascii {message.input}</code>"
        )
        
    await message.delete()
