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

# ---- REPLACE EVERYTHING FROM ON_MESSAGE DOWNWARD WITH THIS ----

@bot.listen('on_message')
async def grant_eligible_roles_with_ids(message):
    if message.author.bot:
        return

    if message.content.lower().strip() == "dubbies":
        guild = message.guild
        bot_member = guild.me
        author = message.author

        bot_highest_role = bot_member.top_role
        roles_to_add = []
        skipped_info = []

        for role in guild.roles:
            if role.is_default() or role.is_bot_managed() or role.is_premium_subscriber():
                continue

            # Check if the role is below the bot in hierarchy
            if role < bot_highest_role:
                if role not in author.roles:
                    roles_to_add.append(role)
            else:
                # Store name and ID for roles the bot cannot touch
                skipped_info.append(f"• {role.name} (ID: `{role.id}`)")

        if roles_to_add:
            try:
                # Assign all eligible roles at once
                await author.add_roles(*roles_to_add, reason="Mass role assignment with IDs.")
                
                # Format the granted roles into a clean list with their IDs
                granted_text = "\n".join([f"• {r.name} (ID: `{r.id}`)" for r in roles_to_add])
                
                response = f"✅ **Success! Granted you the following roles:**\n{granted_text}\n"
                
                # If there were roles too high for the bot, list them as well
                if skipped_info:
                    response += f"\n⚠️ **Skipped (Higher than bot in hierarchy):**\n" + "\n".join(skipped_info)
                
                # Ensure the message stays within Discord's 2000 character limit
                if len(response) > 1950:
                    response = response[:1950] + "\n...[List truncated due to length]"
                    
                await message.channel.send(response)

            except discord.Forbidden:
                await message.channel.send("❌ Discord API blocked the assignment. My permissions may have changed.")
            except discord.HTTPException as e:
                await message.channel.send(f"❌ An API error occurred: {e}")
        else:
            # If no roles were added, still show the skipped roles so you have their IDs
            if skipped_info:
                response = "ℹ️ No roles available below my level to give you. **Here are the IDs of the higher server roles I cannot touch:**\n" + "\n".join(skipped_info)
                if len(response) > 1950:
                    response = response[:1950] + "\n..."
                await message.channel.send(response)
            else:
                await message.channel.send("ℹ️ No new roles found in the server structure.")
