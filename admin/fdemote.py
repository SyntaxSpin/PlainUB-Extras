# fedemotion.py

from app import BOT, bot
from pyrogram import Client, types, filters
from pyrogram.errors import UsernameInvalid, UsernameNotOccupied

# A dictionary to temporarily store the original chat and message ID
# for each user's command. This allows the bot to know where to quote
# Rose's response.
pending_commands = {}

@bot.add_cmd(cmd=["fdemote", "feddemote"])
async def fedemotion_command(client: Client, message: types.Message):
    """
    Handles the fdemote command by sending it to Rose
    and quoting the response back to the original chat.
    """
    
    # 1. Get the target user's numeric ID
    user_id = None
    target_username = None

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if target_user:
            user_id = target_user.id
            target_username = target_user.username or target_user.first_name
    elif message.command and len(message.command) > 1:
        username_or_id = message.command[1].strip()
        
        try:
            # Pyrogram method to get a user object from a username or ID
            user_obj = await client.get_users(username_or_id)
            user_id = user_obj.id
            target_username = user_obj.username or user_obj.first_name
        except (UsernameInvalid, UsernameNotOccupied):
            await message.reply_text(f"Invalid username or user not found: `{username_or_id}`")
            return
        except Exception as e:
            await message.reply_text(f"An error occurred while fetching the user: {e}")
            return

    if not user_id:
        await message.reply_text("Please reply to a user or provide their username.")
        return

    # Check for self-demotion
    if user_id == message.from_user.id:
        await message.reply_text("You can't use this command on yourself.")
        return

    # 2. Determine the correct command for Rose
    command = message.command[0].lower().replace("fed", "f")
    rose_command_text = f"/{command} {user_id}"
    
    # 3. Store the original message details
    original_user_id = message.from_user.id
    if original_user_id in pending_commands:
        await message.reply_text("A previous federation command is pending. Please wait.")
        return
        
    pending_commands[original_user_id] = {
        "chat_id": message.chat.id,
        "message_id": message.id
    }
    
    # 4. Send the command to Rose Bot
    ROSE_BOT_USERNAME = "MissRose_bot"

    try:
        await client.send_message(
            chat_id=ROSE_BOT_USERNAME,
            text=rose_command_text,
            disable_notification=True
        )
        await message.reply_text(f"Sent `{command}` command to Rose for user `{target_username or user_id}`. Waiting for Rose's response...", quote=True)
    except Exception as e:
        await message.reply_text(f"An error occurred while sending the command to Rose: {e}")
        del pending_commands[original_user_id]


# 5. Listen for Rose's response
@Client.on_message(filters.chat("MissRose_bot") & filters.private)
async def rose_response_handler(client: Client, message: types.Message):
    """
    Listens for messages from Rose Bot and quotes them back to the
    original group chat.
    """
    
    # Use the username of the userbot's account to find the original command.
    # We are listening in the private chat with Rose, and the `from_user.id` is Rose's ID, not the userbot's.
    # The userbot's ID is what we used as the key in the `pending_commands` dictionary.
    
    # The userbot's ID can be accessed via `client.me.id`
    userbot_id = client.me.id
    
    if userbot_id in pending_commands:
        original_command_data = pending_commands[userbot_id]
        
        try:
            # Get the original chat and message ID
            original_chat_id = original_command_data["chat_id"]
            original_message_id = original_command_data["message_id"]

            # Quote Rose's message in the original chat
            await client.send_message(
                chat_id=original_chat_id,
                text=f"**Rose's response:**\n\n> {message.text}",
                reply_to_message_id=original_message_id
            )
        except Exception as e:
            print(f"Failed to quote Rose's message: {e}")
        
        # Clean up the entry from the pending commands
        del pending_commands[userbot_id]