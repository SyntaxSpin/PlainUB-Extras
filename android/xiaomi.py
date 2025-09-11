# xiaomi.py

from app import BOT, bot
from pyrogram import Client, types, filters

# A dictionary to temporarily store the original chat and message ID
# for each user's command. This allows the bot to know where to quote
# the Xiaomi bot's response.
pending_commands = {}

@bot.add_cmd(cmd=["whatis", "xiaomi"])
async def xiaomi_lookup_command(client: Client, message: types.Message):
    """
    Looks up a Xiaomi device from its codename using @xiaomigeeksbot.
    """
    
    # 1. Get the codename from the command
    if not message.command or len(message.command) < 2:
        await message.reply_text("Please provide a codename. Example: `.whatis ruby`")
        return

    codename = message.command[1].strip()
    
    # 2. Store the original message details
    original_user_id = message.from_user.id
    if original_user_id in pending_commands:
        await message.reply_text("A previous Xiaomi lookup is pending. Please wait.")
        return
        
    pending_commands[original_user_id] = {
        "chat_id": message.chat.id,
        "message_id": message.id
    }
    
    # 3. Send the command to the Xiaomi bot
    XIAOMI_BOT_USERNAME = "xiaomigeeksbot"
    xiaomi_command_text = f"/whatis {codename}"

    try:
        await client.send_message(
            chat_id=XIAOMI_BOT_USERNAME,
            text=xiaomi_command_text,
            disable_notification=True
        )
        await message.reply_text(f"Sent lookup command for `{codename}` to Xiaomi bot. Waiting for a response...", quote=True)
    except Exception as e:
        await message.reply_text(f"An error occurred while sending the command to the Xiaomi bot: {e}")
        del pending_commands[original_user_id]


# 4. Listen for the Xiaomi bot's response
@Client.on_message(filters.chat("xiaomigeeksbot") & filters.private)
async def xiaomi_response_handler(client: Client, message: types.Message):
    """
    Listens for messages from @xiaomigeeksbot and quotes them back
    to the original group chat.
    """
    
    # The userbot's ID is used as the key in the pending_commands dictionary.
    userbot_id = client.me.id
    
    if userbot_id in pending_commands:
        original_command_data = pending_commands[userbot_id]
        
        try:
            # Get the original chat and message ID
            original_chat_id = original_command_data["chat_id"]
            original_message_id = original_command_data["message_id"]

            # Quote the Xiaomi bot's message in the original chat
            await client.send_message(
                chat_id=original_chat_id,
                text=f"**Xiaomi Bot's response:**\n\n> {message.text}",
                reply_to_message_id=original_message_id
            )
        except Exception as e:
            print(f"Failed to quote the Xiaomi bot's message: {e}")
        
        # Clean up the entry from the pending commands
        del pending_commands[userbot_id]