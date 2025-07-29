import io
import textwrap

try:
    import cowsay
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    cowsay = None
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

@bot.add_cmd(cmd=["cowsay", "csay"])
async def cowsay_cmd_img(bot: BOT, message: Message):
    """
    CMD: COWSAY / CSAY
    INFO: Generates an image of an ASCII art cow with a speech bubble.
    USAGE:
        .cowsay <text>
    """
    if not cowsay or not Image:
        await message.edit(
            "<b>Required libraries not found.</b>\n"
            "Please install them using: <code>pip install cowsay Pillow</code>"
        )
        return

    if not message.input:
        await message.edit("What should the cow say? Provide some text.", del_in=5)
        return

    progress_msg = await message.edit("<code>Generating...</code>")
    text_to_say = message.input
    
    wrapped_text = "\n".join(textwrap.wrap(text_to_say, width=40))
    cowsay_text = cowsay.cow(wrapped_text)

    font = ImageFont.load_default()
    
    lines = cowsay_text.split('\n')
    longest_line = max(lines, key=len)
    char_width = font.getbbox(" ")[2]
    line_height = font.getbbox("A")[3] + 4
    
    img_width = int(len(longest_line) * char_width) + 40
    img_height = int(len(lines) * line_height) + 40
    img_size = (img_width, img_height)

    img = Image.new('RGB', img_size, color='black')
    draw = ImageDraw.Draw(img)

    draw_monospace_text(draw, cowsay_text, (20, 20), font, 'white')

    await progress_msg.edit("<code>Uploading...</code>")
    
    with io.BytesIO() as bio:
        bio.name = 'cowsay.png'
        img.save(bio, 'PNG')
        bio.seek(0)
        
        await message.reply_photo(
            photo=bio,
            caption=f"<code>.cowsay {message.input}</code>"
        )
        
    await message.delete()
