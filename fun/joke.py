import html
import requests
import asyncio
from pyrogram.types import Message

from app import BOT, bot

API_URL = "https://official-joke-api.appspot.com/random_joke"

def safe_escape(text: str) -> str:
    escaped_text = html.escape(str(text))
    return escaped_text.replace("&#x27;", "’")

def sync_get_joke() -> dict:
    """Synchronously fetches a random joke."""
    response = requests.get(API_URL)
    response.raise_for_status()
    return response.json()

@bot.add_cmd(cmd="joke")
async def joke_handler(bot: BOT, message: Message):
    """
    CMD: JOKE
    INFO: Tells you a random joke.
    USAGE: .joke
    """
    
    await message.edit("Finding a good joke... 😂")
    
    try:
        joke_data = await asyncio.to_thread(sync_get_joke)
        
        setup = joke_data.get("setup")
        punchline = joke_data.get("punchline")
        
        if not setup or not punchline:
            raise ValueError("Invalid joke format received from API.")
            
        await message.edit(f"<b>{html.escape(setup)}</b>")
        await asyncio.sleep(3)
        await message.edit(
            f"<b>{html.escape(setup)}</b>\n\n<i>...{html.escape(punchline)}</i>"
        )

    except Exception as e:
        await message.edit(f"<b>Error:</b> Could not fetch a joke.\n<code>{html.escape(str(e))}</code>")
        await asyncio.sleep(5)
        await message.delete()
