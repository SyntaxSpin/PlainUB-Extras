import asyncio
from datetime import datetime, timezone

from pyrogram import filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from app import BOT, bot

try:
    from app.plugins.tg_tools.pm_permit import ALLOWED_USERS
    PM_PERMIT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    ALLOWED_USERS = []
    PM_PERMIT_AVAILABLE = False


AFK_DATA = {
    "is_afk": False,
    "start_time": None,
    "reason": None
}

def format_duration(start_time: datetime) -> str:
    if not start_time:
        return "a while"
    
    duration = datetime.now(timezone.utc) - start_time
    seconds = int(duration.total_seconds())
    
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days > 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    if seconds > 0:
        parts.append(f"{seconds} second{'s' if seconds > 1 else ''}")
        
    return ", ".join(parts) if parts else "just now"

@bot.add_cmd(cmd="afk")
async def set_afk_handler(bot: BOT, message: Message):
    AFK_DATA["start_time"] = datetime.now(timezone.utc)
    AFK_DATA["reason"] = message.input or "No reason specified."
    AFK_DATA["is_afk"] = True
    
    reason_text = f"<b>Reason:</b> {AFK_DATA['reason']}"
    
    await message.edit(f"You are now AFK.\n{reason_text}")
    await asyncio.sleep(5)
    await message.delete()

async def afk_ping_handler(client: BOT, message: Message):
    if not AFK_DATA["is_afk"] or (message.from_user and message.from_user.is_self):
        return

    is_private = message.chat.is_private
    is_mentioned = message.mentioned
    is_reply_to_me = False
    
    if message.reply_to_message:
        if message.reply_to_message.from_user and message.reply_to_message.from_user.is_self:
            is_reply_to_me = True

    should_send_reply = False
    if is_mentioned or is_reply_to_me:
        should_send_reply = True
    elif is_private:
        if not PM_PERMIT_AVAILABLE or message.from_user.id in ALLOWED_USERS:
            should_send_reply = True

    if should_send_reply:
        time_afk = format_duration(AFK_DATA['start_time'])
        reason = AFK_DATA['reason']

        await message.reply(
            f"Hey! I'm currently AFK.\n"
            f"<b>Been away for:</b> {time_afk}\n"
            f"<b>Reason:</b> {reason}"
        )

async def afk_stop_handler(client: BOT, message: Message):
    if AFK_DATA["is_afk"]:
        if message.text and message.text.lower().startswith(".afk"):
            return

        start_time = AFK_DATA['start_time']
        AFK_DATA["is_afk"] = False
        AFK_DATA["start_time"] = None
        AFK_DATA["reason"] = None
        
        time_afk = format_duration(start_time)
        
        welcome_back_message = await client.send_message(
            chat_id=message.chat.id,
            text=f"<b>Welcome back!</b>\nYou were AFK for {time_afk}."
        )
        await asyncio.sleep(5)
        await welcome_back_message.delete()


bot.add_handler(MessageHandler(afk_stop_handler, filters.outgoing), group=1)
bot.add_handler(MessageHandler(afk_ping_handler, ~filters.outgoing & ~filters.service & ~filters.bot), group=2)
