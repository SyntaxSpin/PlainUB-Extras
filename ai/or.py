import os
from openai import OpenAI
from app import BOT, bot, Message

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

@bot.add_cmd(cmd="or")
async def openrouter_handler(bot: BOT, message: Message):
    reply_to = message.reply_to_message
    prompt = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    
    if not prompt and not reply_to:
        await message.reply("Please provide a prompt or reply to a message.")
        return
    messages = []
    if reply_to and reply_to.photo:
        file_path = await bot.download_media(reply_to)
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt or "Describe this image."},
                {"type": "image_url", "image_url": {"url": f"file://{file_path}"}}
            ]
        })
    else:
        messages.append({"role": "user", "content": prompt})
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-exp", # Or any model from OpenRouter
            messages=messages
        )
        
        reply_text = response.choices[0].message.content
        await message.reply(reply_text)
        
    except Exception as e:
        await message.reply(f"API Error: {str(e)}")
