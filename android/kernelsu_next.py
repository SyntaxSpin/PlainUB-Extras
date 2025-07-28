from app import BOT, bot, Message
from .utils import get_android_versions

@bot.add_cmd(cmd="kernelsunext")
async def kernelsunext_handler(bot: BOT, message: Message):
    """CMD: KERNELSUNEXT - Gets the latest KernelSU-Next release."""
    await get_android_versions(bot, message, owner="KernelSU-Next", repo="KernelSU-Next", show_both=False)
