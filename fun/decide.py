import random
from pyrogram.types import Message

from app import BOT, bot

DECIDE_RESPONSES = [
    "Yes, definitely.", "No, absolutely not.", "Maybe, think about it.",
    "The answer is unclear, try again.", "Go for it!", "I wouldn't recommend it.",
    "Signs point to yes.", "Don't count on it.", "Without a doubt.", "My sources say no.",
]

@bot.add_cmd(cmd="decide")
async def decide_handler(bot: BOT, message: Message):
    """
    CMD: DECIDE
    INFO: Helps you make a decision.
    USAGE: .decide
    """
    
    decision = random.choice(DECIDE_RESPONSES)
    final_text = f"🤔 <b>My decision is:</b>\n\n» <i>{decision}</i>"

    await message.edit(final_text)
