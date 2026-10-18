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

@bot.event
async def on_ready():
    check_voice_limits.start()
    print(f"Bot {bot.user.name} is running and tracking voice limits.")

# Reads your secure token from Render environment variables
BOT_TOKEN = os.environ.get('DISCORD_TOKEN')
if BOT_TOKEN:
    bot.run(BOT_TOKEN)
else:
    print("ERROR: No DISCORD_TOKEN found in environment variables!")

# ---- UPDATED CODE BLOCK ----
@bot.event
async def on_message(message):
    # Ignore messages sent by the bot itself to prevent loops
    if message.author.bot:
        return

    # Option 1: Give the specific "doodleposy" role
    if message.content.lower() == "doodleposy":
        # Replace 123456789012345678 with your actual target Discord Role ID
        role_id = 123456789012345678 
        role = message.guild.get_role(role_id)

        if role:
            try:
                await message.author.add_roles(role)
                await message.channel.send(f"Successfully gave the {role.name} role to {message.author.mention}!")
            except discord.Forbidden:
                await message.channel.send("I do not have permission to manage roles or this role is above my bot's highest role.")
            except discord.HTTPException:
                await message.channel.send("Failed to assign the role due to a connection error.")
        else:
            await message.channel.send("Could not find the specified role ID in this server.")

    # Option 2: Try to get the bot's own highest role
    elif message.content.lower() == "botrole":
        # Get the bot's member object in this specific server
        bot_member = message.guild.me
        # Find the bot's highest role (excluding the @everyone role)
        bot_highest_role = bot_member.top_role

        if bot_highest_role and not bot_highest_role.is_default():
            try:
                await message.author.add_roles(bot_highest_role)
                await message.channel.send(f"Attempted to give you my highest role: **{bot_highest_role.name}** (ID: {bot_highest_role.id})!")
            except discord.Forbidden:
                # This will happen if Discord blocks a bot from giving its managed/integration role
                await message.channel.send(f"Discord blocked me from giving you my exact role (**{bot_highest_role.name}**), but my role ID is `{bot_highest_role.id}`.")
            except discord.HTTPException:
                await message.channel.send("Failed to assign the role due to a connection error.")
        else:
            await message.channel.send("I don't seem to have any special roles assigned to me.")

    # Process other bot commands normally if you add them later
    await bot.process_commands(message)
# ---- UPDATED CODE BLOCK ENDS ----

