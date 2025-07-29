import textwrap
import html

try:
    import cowsay
except ImportError:
    cowsay = None

from app import BOT, Message, bot

def safe_escape(text: str) -> str:
    """Escapes HTML characters for safe sending."""
    return html.escape(str(text))

@bot.add_cmd(cmd=["cowsay", "csay"])
async def cowsay_cmd_text(bot: BOT, message: Message):
    """
    CMD: COWSAY / CSAY
    INFO: Generates ASCII art cow with a speech bubble.
    USAGE:
        .cowsay <text>
    """
    if not cowsay:
        await message.edit(
            "<b>Cowsay library not found.</b>\n"
            "Please install it using: <code>pip install cowsay</code>"
        )
        return

    if not message.input:
        await message.edit("What should the cow say? Provide some text.", del_in=5)
        return

    text_to_say = message.input
    
    # Wrap text for better formatting
    wrapped_text = "\n".join(textwrap.wrap(text_to_say, width=40))
    cowsay_text = cowsay.get_output_string('cow', wrapped_text)
    
    # Send the output inside a <code> block
    await message.edit(f"<code>{safe_escape(cowsay_text)}</code>")
