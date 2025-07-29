import os
import html
import asyncio
import json
from pyrogram.types import Message, ReplyParameters

from app import BOT, bot

ERROR_VISIBLE_DURATION = 8

def safe_escape(text: str) -> str:
    """Escapes HTML characters for safe sending inside HTML tags."""
    return html.escape(str(text))

def json_cleaner(o):
    """A custom serializer for json.dumps to handle Pyrogram objects."""
    if hasattr(o, '__dict__'):
        clean_dict = {}
        for key, value in o.__dict__.items():
            if not key.startswith('_'):
                clean_dict[key] = value
        return clean_dict
    try:
        return str(o)
    except:
        raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")


@bot.add_cmd(cmd="json")
async def dev_handler(bot: BOT, message: Message):
    """
    CMD: JSON
    INFO: Shows the raw Pyrogram message object as a formatted JSON.
    USAGE:
        .dev (shows info about the command message)
        .dev (in reply to a message, shows info about that message)
    """
    
    target_message = message.replied or message
    
    progress_message = await message.reply("<code>Serializing message object to JSON...</code>")
    
    try:
        # Convert the message object to a clean, indented JSON string
        message_data_str = json.dumps(
            target_message,
            indent=4,
            default=json_cleaner,
            ensure_ascii=False
        )
        
        # 1. Escape only the JSON content
        safe_json_content = safe_escape(message_data_str)
        
        # 2. Place it inside the simplified <pre> tag with a class
        final_report = f'<pre class="language-json">{safe_json_content}</pre>'
        
        # Truncate if necessary
        if len(final_report) > 4096:
            overhead_len = len('<pre class="language-json"></pre>\n... (truncated)')
            max_json_len = 4096 - overhead_len
            
            truncated_data = safe_escape(message_data_str[:max_json_len])
            final_report = f'<pre class="language-json">{truncated_data}\n... (truncated)</pre>'

        # Send the report as a reply
        await bot.send_message(
            chat_id=message.chat.id,
            text=final_report,
            reply_parameters=ReplyParameters(message_id=target_message.id)
        )
        
        # Final cleanup
        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not process message.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
        try:
            await message.delete()
        except:
            pass
