from app import BOT, bot, Message
from .utils import get_android_versions

@bot.add_cmd(cmd="magisk")
async def magisk_handler(bot: BOT, message: Message):
    """CMD: MAGISK - Gets latest Magisk stable & pre-release."""
    await get_android_versions(bot, message, owner="topjohnwu", repo="Magisk", show_both=True)
