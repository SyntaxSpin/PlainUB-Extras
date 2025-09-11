from app import BOT, bot
from pyrogram import Client, types, filters

# The command decorator from Plain Userbot
@bot.add_cmd(cmd=["fdemote", "feddemote"])
async def fdemote_command(client: Client, message: types.Message):
    """
    Demotes a user from a Rose federation.
    """
    
    # 1. Get the target user ID
    target_user_id = None
    if message.reply_to_message:
        # If the command is a reply, get the ID from the replied message
        target_user_id = message.reply_to_message.from_user.id
        target_username = message.reply_to_message.from_user.username
    elif len(message.command) > 1:
        # If a username is provided in the command
        target_username = message.command[1].strip("@")
        # You'll need to look up the user ID from the username
        # This can be done with Pyrogram's get_users() method, but it's
        # more complex. For simplicity, we'll assume a username is enough
        # to pass to Rose.
    else:
        await message.reply_text("Please reply to a user or provide their username.")
        return

    # A simple check to prevent self-demotion
    if target_user_id == message.from_user.id:
        await message.reply_text("You can't fdemote yourself.")
        return

    # Get the ID of the Rose bot
    # This is a public bot, so its username is @MissRose_bot
    ROSE_BOT_USERNAME = "MissRose_bot"

    # 2. Construct the command to send to Rose
    # The format Rose expects is likely "/fdemote <user ID or username>"
    # We will send the fdemote command with the username to be safe.
    fdemote_command_text = f"/fdemote @{target_username}"

    # 3. Send the command to Rose in a private chat (DM)
    # The 'client.send_message()' method from Pyrogram is what you need.
    try:
        # Use a silent message to avoid notifications
        await client.send_message(
            chat_id=ROSE_BOT_USERNAME,
            text=fdemote_command_text,
            disable_notification=True
        )

        # Optional: You can try to wait for a response from Rose in that private chat,
        # but that can be complex to implement reliably. For a simple plugin,
        # we can just send a confirmation message.

        # 4. Acknowledge to the user that the command was sent.
        await message.reply_text(f"Sent fdemote command for @{target_username} to Rose bot. Check our PM with Rose for the result.")

    except Exception as e:
        # Handle potential errors, like if the bot can't send messages
        # to Rose.
        await message.reply_text(f"An error occurred: {e}")