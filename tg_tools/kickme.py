import html
import asyncio
from pyrogram.types import Message

from app import BOT, bot

async def _delayed_leave(chat_id: int | str):
    await asyncio.sleep(1)
    await bot.leave_chat(chat_id)

@bot.add_cmd(cmd=["leave", "kickme"])
async def leave_chat_handler(bot: BOT, message: Message):
    """
    CMD: LEAVE / KICKME
    INFO: Leaves a chat or channel.
    USAGE:
        .leave (leaves the current chat)
        .leave [chat_id] (leaves a specific chat)
    """
    
    try:
        if message.input:
            chat_id_to_leave = message.input.strip()
            
            try:
                chat_id_to_leave = int(chat_id_to_leave)
            except ValueError:
                pass

            await bot.leave_chat(chat_id_to_leave)
            
            confirmation_msg = await message.reply(
                f"<code>Successfully left</code>"
            )
            await asyncio.sleep(8)
            await confirmation_msg.delete()
            await message.delete()
        else:
            asyncio.create_task(_delayed_leave(message.chat.id))

    except Exception as e:
        await message.reply(f"<b>Error:</b> Could not leave chat.\n<code>{html.escape(str(e))}</code>", del_in=10)
