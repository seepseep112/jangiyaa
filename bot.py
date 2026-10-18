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
        if duration.total_seconds() >= 10: 
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
