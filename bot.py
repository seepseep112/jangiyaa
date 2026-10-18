import discord
from discord.ext import tasks, commands
import datetime
import os

# Initialize bot with intents to track voice states
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True  # Add this exact line here!
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to keep track of when users join a voice channel
voice_tracker = {}

@bot.event
async def on_voice_state_update(member, before, after):
    # User joins a voice channel
    if before.channel is None and after.channel is not None:
        voice_tracker[member.id] = datetime.datetime.now(datetime.timezone.utc)
    
    # User disconnects from all voice channels
    elif before.channel is not None and after.channel is None:
        voice_tracker.pop(member.id, None)

# This background task runs every 1 minute to check user durations
@tasks.loop(minutes=1)
async def check_voice_limits():
    now = datetime.datetime.now(datetime.timezone.utc)
    for member_id, join_time in list(voice_tracker.items()):
        duration = now - join_time
        
        # 10800 seconds = 3 hours
        if duration.total_seconds() >= 1000: 
            for guild in bot.guilds:
                member = guild.get_member(member_id)
                if member and member.voice and member.voice.channel:
                    try:
                        # Set timeout penalty duration (e.g., 1 hour)
                        penalty_duration = datetime.timedelta(hours=1)
                        await member.timeout(penalty_duration, reason="Exceeded 3-hour voice chat limit.")
                        
                        # Disconnect them from the voice channel instantly
                        await member.move_to(None)
                        voice_tracker.pop(member_id, None)
                        print(f"Timed out {member.name} for exceeding 3 hours.")
                    except Exception as e:
                        print(f"Could not timeout {member.name}: {e}")

# ---- FINALIZED ROLE ASSIGNMENT CODE ----
@bot.event
async def on_message(message):
    # Ignore messages sent by the bot itself to prevent loops
    if message.author.bot:
        return

    # Check if the text matches "doodleposy" (case-insensitive)
    if message.content.lower() == "doodleposy":
        # PASTE YOUR NEWLY FOUND ROLE ID NUMBER HERE (No quotes)
        role_id = 1561325628320653354
        
        role = message.guild.get_role(role_id)

        if role:
            try:
                await message.author.add_roles(role)
                await message.channel.send(f"Successfully gave the **{role.name}** role to {message.author.mention}!")
            except discord.Forbidden:
                await message.channel.send("I couldn't give you the role. Make sure my bot role is higher than that role in the server settings hierarchy!")
            except discord.HTTPException:
                await message.channel.send("Failed to assign the role due to a Discord connection error.")
        else:
            await message.channel.send("I couldn't find that role ID in this server. Double-check that the ID is correct!")

    # This ensures your regular "!" commands still function properly
    await bot.process_commands(message)
# ----------------------------------------
