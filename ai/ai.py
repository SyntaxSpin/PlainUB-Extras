import os
import html
import asyncio
import requests
from pyrogram.types import Message, ReplyParameters

from app import BOT, bot

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.dirname(SCRIPT_DIR)
ENV_PATH = os.path.join(MODULES_DIR, "extra_config.env")
from dotenv import load_dotenv
load_dotenv(dotenv_path=ENV_PATH)
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
ERROR_VISIBLE_DURATION = 15
TELEGRAM_MSG_LIMIT = 4096

@bot.add_cmd(cmd="ask")
async def ask_handler(bot: BOT, message: Message):
    """
    CMD: ASK
    INFO: Asks a question to the Llama 3 AI model and handles long responses.
    USAGE:
        .ask [question]
        .ask (in reply to a message to use its text as context)
    """
    if not CF_ACCOUNT_ID or not CF_API_TOKEN or "YOUR_KEY" in CF_API_TOKEN:
        return await message.reply("<b>Cloudflare AI not configured.</b>", del_in=ERROR_VISIBLE_DURATION)

    prompt = message.input
    display_prompt = prompt
    if message.replied and message.replied.text:
        replied_text = message.replied.text
        if prompt:
            display_prompt = f"(In reply to text) {prompt}"
            prompt = f"Based on the following text:\n---\n{replied_text}\n---\nAnswer this question: {prompt}"
        else:
            display_prompt = "(Summarizing replied text)"
            prompt = f"Summarize or analyze the following text:\n{replied_text}"

    if not prompt: return await message.reply("<b>Usage:</b> .ask [question]", del_in=ERROR_VISIBLE_DURATION)

    progress_message = await message.reply("<code>Thinking...</code>")
    try:
        api_url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/@cf/meta/llama-3-8b-instruct"
        headers = {"Authorization": f"Bearer {CF_API_TOKEN}"}
        
        # Request a long response from the AI
        payload = {
            "messages": [{"role": "system", "content": "You are a helpful AI assistant."}, {"role": "user", "content": prompt}]
        }
        
        response = await asyncio.to_thread(requests.post, api_url, headers=headers, json=payload, timeout=300)
        response.raise_for_status()
        response_data = response.json()
        
        if response_data.get("success"):
            ai_response = response_data["result"]["response"].strip()
            
            header = f"<b>Prompt:</b> <i>{html.escape(display_prompt)}</i>\n\n"
            safe_ai_response = html.escape(ai_response)
            
            
            full_message = f"{header}<pre>{safe_ai_response}</pre>"

            if len(full_message) <= TELEGRAM_MSG_LIMIT:
                # If it fits in one message, send it and we're done
                await bot.send_message(
                    chat_id=message.chat.id, text=full_message,
                    reply_parameters=ReplyParameters(message_id=message.id)
                )
            else:
                # If it's too long, split it into multiple messages
                
                # First message with header
                header_len = len(header)
                first_chunk_max_len = TELEGRAM_MSG_LIMIT - header_len - len("<pre></pre>... (continued)")
                
                # Find a safe place to split (at a newline)
                split_pos = ai_response.rfind('\n', 0, first_chunk_max_len)
                if split_pos == -1: split_pos = first_chunk_max_len

                first_chunk = ai_response[:split_pos]
                remaining_text = ai_response[split_pos:].strip()

                first_message_text = f"{header}<pre>{html.escape(first_chunk)}\n... (continued)</pre>"
                sent_message = await bot.send_message(
                    chat_id=message.chat.id, text=first_message_text,
                    reply_parameters=ReplyParameters(message_id=message.id)
                )
                
                # Subsequent messages
                while remaining_text:
                    await asyncio.sleep(1) # Small delay to avoid flooding
                    
                    chunk_max_len = TELEGRAM_MSG_LIMIT - len("<pre>... (continued)</pre>")
                    
                    split_pos = remaining_text.rfind('\n', 0, chunk_max_len)
                    if len(remaining_text) > chunk_max_len and split_pos != -1:
                        chunk = remaining_text[:split_pos]
                        remaining_text = remaining_text[split_pos:].strip()
                        chunk_text = f"<pre>{html.escape(chunk)}\n... (continued)</pre>"
                    else:
                        chunk = remaining_text
                        remaining_text = ""
                        chunk_text = f"<pre>{html.escape(chunk)}</pre>"

                    sent_message = await bot.send_message(
                        chat_id=message.chat.id, text=chunk_text,
                        reply_parameters=ReplyParameters(message_id=sent_message.id)
                    )

            await progress_message.delete(); await message.delete()
        else:
            raise Exception(f"API Error: {response_data.get('errors') or 'Unknown error'}")

    except requests.exceptions.Timeout:
         await progress_message.edit("<b>Error:</b> The request to the AI timed out.", del_in=ERROR_VISIBLE_DURATION)
    except Exception as e:
        await progress_message.edit(f"<b>Error:</b> Could not get a response.\n<code>{html.escape(str(e))}</code>", del_in=ERROR_VISIBLE_DURATION)
