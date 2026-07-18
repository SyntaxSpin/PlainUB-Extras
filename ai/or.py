import os
import requests
import base64
from openai import OpenAI
from app import BOT, bot, Message, Config

api_key = Config.OPENROUTER_API_KEY
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

CURRENT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

@bot.add_cmd(cmd="orllm")
async def model_manager(bot: BOT, message: Message):
    global CURRENT_MODEL
    args = message.text.split(maxsplit=2)
    
    if len(args) > 1 and args[1] == "list":
        try:
            response = requests.get("https://openrouter.ai/api/v1/models")
            models = response.json().get("data", [])
            model_names = "\n".join([f"- {m['id']}" for m in models[:20]])
            await message.reply(f"Available models:\n{model_names}\n\nUse '.orllm set <model_id>'")
        except Exception as e:
            await message.reply(f"Error: {e}")
            
    elif len(args) > 2 and args[1] == "set":
        CURRENT_MODEL = args[2]
        await message.reply(f"Model set to: {CURRENT_MODEL}")
        
    else:
        await message.reply(f"Current model: {CURRENT_MODEL}")

@bot.add_cmd(cmd="or")
async def openrouter_handler(bot: BOT, message: Message):
    prompt = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "Describe this."
    reply_to = message.reply_to_message
    messages = []

    if reply_to and reply_to.photo:
        file_path = await bot.download_media(reply_to)
        with open(file_path, "rb") as image_file:
            b64_image = base64.b64encode(image_file.read()).decode('utf-8')
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
            ]
        })
    else:
        messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(model=CURRENT_MODEL, messages=messages)
        await message.reply(response.choices[0].message.content)
    except Exception as e:
        await message.reply(f"Error: {str(e)}")
