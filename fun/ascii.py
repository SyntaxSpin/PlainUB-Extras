import html

try:
    from pyfiglet import figlet_format
except ImportError:
    figlet_format = None

from app import BOT, Message, bot

def safe_escape(text: str) -> str:
    """Escapes HTML characters for safe sending."""
    return html.escape(str(text))

@bot.add_cmd(cmd=["ascii", "figlet"])
async def ascii_cmd_text(bot: BOT, message: Message):
    """
    CMD: ASCII / FIGLET
    INFO: Generates large ASCII art text.
    USAGE:
        .ascii <text>
    """
    if not figlet_format:
        await message.edit(
            "<b>PyFiglet library not found.</b>\n"
            "Please install it using: <code>pip install pyfiglet</code>"
        )
        return
        
    if not message.input:
        await message.edit("What should I write in ASCII? Provide some text.", del_in=5)
        return

    text_to_render = message.input
    
    try:
        # Generate the ASCII art using a standard font
        ascii_art = figlet_format(text_to_render, font='standard')
        # Send the output inside a <code> block
        await message.edit(f"<code>{safe_escape(ascii_art)}</code>")
    except Exception as e:
        await message.edit(f"<b>An error occurred:</b>\n<code>{e}</code>")
