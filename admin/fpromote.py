from app import BOT, bot
from pyrogram import Client, types, filters

@bot.add_cmd(cmd=["fpromote", "fedpromote"])
async def fpromote_command(client: Client, message: types.Message):
    """
    Promotes a user in a Rose federation.
    """
    
    # 1. Get the target user ID
    target_user_id = None
    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
        target_username = message.reply_to_message.from_user.username
    elif len(message.command) > 1:
        target_username = message.command[1].strip("@")
    else:
        await message.reply_text("Please reply to a user or provide their username.")
        return

    # Check to prevent self-promotion
    if target_user_id == message.from_user.id:
        await message.reply_text("You can't fpromote yourself.")
        return
        
    ROSE_BOT_USERNAME = "MissRose_bot"

    # 2. Construct the command to send to Rose
    fpromote_command_text = f"/fpromote @{target_username}"

    # 3. Send the command to Rose in a private chat (DM)
    try:
        await client.send_message(
            chat_id=ROSE_BOT_USERNAME,
            text=fpromote_command_text,
            disable_notification=True
        )

        # 4. Acknowledge to the user
        await message.reply_text(f"Sent fpromote command for @{target_username} to Rose bot. Check our PM with Rose for the result.")

    except Exception as e:
        await message.reply_text(f"An error occurred: {e}")