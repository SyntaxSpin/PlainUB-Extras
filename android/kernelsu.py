from app import BOT, bot, Message
from .utils import get_android_versions

@bot.add_cmd(cmd="kernelsu")
async def kernelsu_handler(bot: BOT, message: Message):
    """CMD: KERNELSU - Gets latest KernelSU stable & pre-release."""
    await get_android_versions(bot, message, owner="tiann", repo="KernelSU", show_both=True)
