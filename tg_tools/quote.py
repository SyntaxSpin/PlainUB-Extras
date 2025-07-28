import asyncio
import html
from pyrogram import filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from app import BOT, bot

QUOTLY_BOT_ID = 705424444
QUOTLY_TIMEOUT = 15
ERROR_VISIBLE_DURATION = 8

async def wait_for_quotly_response(bot: BOT, timeout: int) -> Message | None:
    queue = asyncio.Queue()
    
    required_filters = filters.user(QUOTLY_BOT_ID)

    async def _handler(_, message: Message):
        await queue.put(message)

    handler = bot.add_handler(MessageHandler(_handler, filters=required_filters), group=-1)

    try:
        return await asyncio.wait_for(queue.get(), timeout=timeout)
    except asyncio.TimeoutError:
        return None
    finally:
        bot.remove_handler(*handler)


@bot.add_cmd(cmd=["q", "quote"])
async def quote_sticker_handler(bot: BOT, message: Message):
    """
    CMD: Q | QUOTE
    INFO: Creates a sticker/image by forwarding messages to @QuotLyBot.
    USAGE: .q [count] (reply to a message)
    """
    if not message.replied:
        await message.edit("Please reply to a message to quote.", del_in=ERROR_VISIBLE_DURATION)
        return

    count = 1
    if message.input and message.input.isdigit():
        count = min(int(message.input), 10)

    progress_message = await message.reply(f"Forwarding {count} message(s) to @QuotLyBot...")
    
    message_ids = range(message.replied.id, message.replied.id + count)
    
    try:
        listener_task = asyncio.create_task(wait_for_quotly_response(bot, QUOTLY_TIMEOUT))
        
        await bot.forward_messages(
            chat_id=QUOTLY_BOT_ID,
            from_chat_id=message.chat.id,
            message_ids=message_ids
        )
        
        quotly_response = await listener_task

        if quotly_response:

            await progress_message.delete()
            await message.delete()

            await quotly_response.forward(message.chat.id)
            
        else:
            raise asyncio.TimeoutError("@QuotLyBot did not respond in time.")

    except Exception as e:
        error_text = f"<b>Error:</b> Could not get a quote from @QuotLyBot.\n<code>{html.escape(str(e))}</code>"
        try:
            await progress_message.edit(error_text)
            await asyncio.sleep(ERROR_VISIBLE_DURATION)
            await progress_message.delete()
        except Exception:
            pass
        
        try:
            await message.delete()
        except Exception:
            pass
