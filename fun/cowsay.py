import io
import contextlib
from cowsay import cow

from app import BOT, Message, bot


@bot.add_cmd(cmd="cowsay")
async def cowsay(bot: BOT, message: Message):
    text = message.input
    if not text:
        await message.reply("What is the cow supposed to say?")
        return

    string_io = io.StringIO()
    
    with contextlib.redirect_stdout(string_io):
        cow(text)
    
    cow_said = string_io.getvalue()

    if cow_said.endswith('\n'):
        cow_said = cow_said[:-1]

    await message.reply(f"```
    {cow_said}
    ```")
