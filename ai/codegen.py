import os
import html
import asyncio
import requests
from pyrogram.types import Message, ReplyParameters, LinkPreviewOptions
from dotenv import load_dotenv

from app import BOT, bot

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.dirname(SCRIPT_DIR)
ENV_PATH = os.path.join(MODULES_DIR, "extra_config.env")
load_dotenv(dotenv_path=ENV_PATH)
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
ERROR_VISIBLE_DURATION = 15

@bot.add_cmd(cmd=["codegen", "cg"])
async def codegen_handler(bot: BOT, message: Message):
    """
    CMD: CODEGEN / CG
    INFO: Generates code based on a natural language prompt using Cloudflare's Code Llama.
    USAGE:
        .codegen [language] (description of the code)
    EXAMPLE:
        .codegen python a function to calculate fibonacci sequence
    """
    if not CF_ACCOUNT_ID or not CF_API_TOKEN or "YOUR_KEY" in CF_API_TOKEN:
        return await message.reply(
            "<b>Cloudflare AI not configured.</b>\n"
            "Please add  CFF_ACCOUNT_ID and CF_API_TOKEN to your extra_config.env file.",
            del_in=ERROR_VISIBLE_DURATION
        )

    if not message.input:
        return await message.reply(
            "<b>Usage:</b> .codegen [language] (description)\n"
            "<b>Example:</b> .codegen python a function that sorts a list",
            del_in=ERROR_VISIBLE_DURATION
        )
    
    parts = message.input.split(maxsplit=1)
    if len(parts) < 2:
        return await message.edit(
            "Please specify both a language and a description.",
            del_in=ERROR_VISIBLE_DURATION
        )
        
    language = parts[0].lower()
    prompt = parts[1]

    progress_message = await message.reply("<code>Generating...</code>")

    try:
        api_url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/@hf/thebloke/codellama-7b-instruct-awq"
        
        headers = {"Authorization": f"Bearer {CF_API_TOKEN}"}
        
        full_prompt = f"In {language}, write a code snippet that does the following: {prompt}"
        payload = {"prompt": full_prompt}
        
        response = await asyncio.to_thread(requests.post, api_url, headers=headers, json=payload)
        response.raise_for_status()
        
        response_data = response.json()
        
        if response_data.get("success"):
            generated_code = response_data["result"]["response"]
            
            code_block = generated_code
            if "```" in generated_code:
                try:
                    code_block = generated_code.split("```")[1]
                    if code_block.lower().startswith(language):
                        code_block = '\n'.join(code_block.split('\n')[1:])
                except IndexError:
                    pass

            final_output = f'<b>Promt:</b> {prompt}\n\n<pre class="language-{language}">{html.escape(code_block.strip())}</pre>'
            
            await bot.send_message(
                chat_id=message.chat.id,
                text=final_output,
                reply_parameters=ReplyParameters(message_id=message.id)
            )
            
            await progress_message.delete()
            await message.delete()
        else:
            raise Exception(f"API Error: {response_data.get('errors') or 'Unknown error'}")

    except Exception as e:
        error_text = f"<b>Error:</b> Could not generate code.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
