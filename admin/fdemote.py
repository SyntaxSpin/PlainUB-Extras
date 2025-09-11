# fdemote.py
from app import BOT, bot
from pyrogram import Client, types, filters
from pyrogram.errors import UsernameInvalid, UsernameNotOccupied

@bot.add_cmd(cmd=["fdemote", "feddemote"])
async def fdemote_command(client: Client, message: types.Message):
    """
    Demotes a user from a Rose federation using their numeric ID.
    """

    user_id = None
    target_username = None

    # Check for a reply first
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if target_user:
            user_id = target_user.id
            target_username = target_user.username or target_user.first_name
    
    # If no reply, check for a username in the command
    elif message.command and len(message.command) > 1:
        username_or_id = message.command[1].strip()
        
        try:
            # Try to get the user's numeric ID from the username
            user_obj = await client.get_users(username_or_id)
            user_id = user_obj.id
            target_username = user_obj.username or user_obj.first_name
        except (UsernameInvalid, UsernameNotOccupied):
            # Handle cases where the username is not found or is invalid
            await message.reply_text(f"Invalid username or user not found: `{username_or_id}`")
            return
        except Exception as e:
            # General error handling
            await message.reply_text(f"An error occurred while fetching the user: {e}")
            return

    # If we couldn't get a user ID from either a reply or a username, show help
    if not user_id:
        await message.reply_text("Please reply to a user or provide their username to fdemote them.")
        return

    # A simple check to prevent self-demotion
    if user_id == message.from_user.id:
        await message.reply_text("You can't fdemote yourself.")
        return

    # Get the ID of the Rose bot
    ROSE_BOT_USERNAME = "MissRose_bot"

    # Construct the command to send to Rose using the numeric ID
    fdemote_command_text = f"/fdemote {user_id}"

    # Send the command to Rose in a private chat (DM)
    try:
        await client.send_message(
            chat_id=ROSE_BOT_USERNAME,
            text=fdemote_command_text,
            disable_notification=True
        )

        # Acknowledge to the user that the command was sent.
        if target_username:
            reply_text = f"Sent fdemote command for user `{target_username}` to Rose bot. Check your PM with Rose for the result."
        else:
            reply_text = f"Sent fdemote command for user with ID `{user_id}` to Rose bot. Check your PM with Rose for the result."
            
        await message.reply_text(reply_text)

    except Exception as e:
        # Handle potential errors, like if the bot can't send messages to Rose.
        await message.reply_text(f"An error occurred while sending the command to Rose: {e}")