import os
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands

app = Flask('')
@app.route('/')
def home(): return "Config Bot Status: Operational"
def run_web(): app.run(host='0.0.0.0', port=10000)

TARGET_USER_ID = 1143856525648076812
LOG_CHANNEL_ID = 1515049160561135747
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

bot = commands.Bot(command_prefix='.', intents=intents, help_command=None)
EMBED_COLOR = 0x2b2d31

async def sync_activity(guild=None):
    member = guild.get_member(TARGET_USER_ID) if guild else None
    if not member:
        for g in bot.guilds:
            member = g.get_member(TARGET_USER_ID)
            if member: break
    if member and member.status != discord.Status.offline:
        await bot.change_presence(status=member.status, activity=member.activity)
    else:
        await bot.change_presence(status=discord.Status.online, activity=None)

async def toggle_role(ctx, role_name, color):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        try: role = await ctx.guild.create_role(name=role_name, color=color, mentionable=True)
        except discord.Forbidden: return await ctx.send("❌ I need 'Manage Roles' permission.")
    if role in ctx.author.roles:
        await ctx.author.remove_roles(role)
        await ctx.send(embed=discord.Embed(description=f"✨ Removed {role.mention} role.", color=EMBED_COLOR))
    else:
        await ctx.author.add_roles(role)
        await ctx.send(embed=discord.Embed(description=f"✨ Assigned {role.mention} role.", color=EMBED_COLOR))

@bot.event
async def on_ready():
    await sync_activity()
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        try: await channel.send(f"<@{TARGET_USER_ID}> online ☕")
        except discord.Forbidden: pass

@bot.event
async def on_presence_update(before, after):
    if after.id == TARGET_USER_ID: await sync_activity(after.guild)

@bot.event
async def on_message(message):
    if message.author.bot: return
    if bot.user.mentioned_in(message) and len(message.content.split()) == 1:
        try:
            await message.add_reaction("🥶")
            await message.channel.send(f"{message.author.mention} the prefix of this server is `.`")
        except discord.Forbidden: pass
        return
    await bot.process_commands(message)

@bot.command(name='roles')
async def roles_list(ctx):
    embed = discord.Embed(title="🎭 Available Self-Roles", description="Use these commands to toggle your notification pings:", color=EMBED_COLOR)
    embed.add_field(name="`.updates`", value="Toggle the `📢┃Updates` role.", inline=True)
    embed.add_field(name="`.announcements`", value="Toggle the `📢┃Announcements` role.", inline=True)
    await ctx.send(embed=embed)

@bot.command(name='updates')
async def updates_cmd(ctx):
    await toggle_role(ctx, "📢┃Updates", discord.Color.blue())

@bot.command(name='announcements')
async def announcements_cmd(ctx):
    await toggle_role(ctx, "📢┃Announcements", discord.Color.gold())

@bot.command(name='list')
async def list_help(ctx):
    embed = discord.Embed(title="🛠️ System Core Command List", description="Current operational framework commands:", color=EMBED_COLOR)
    embed.add_field(name="`.list`", value="Displays this core diagnostics list.", inline=False)
    embed.add_field(name="`.roles`", value="Shows all self-assignable public roles.", inline=False)
    embed.add_field(name="`.updates`", value="Get or remove the updates ping role.", inline=True)
    embed.add_field(name="`.announcements`", value="Get or remove the announcements ping role.", inline=True)
    await ctx.send(embed=embed)

Thread(target=run_web).start()
bot.run(os.environ.get("DISCORD_TOKEN"))
