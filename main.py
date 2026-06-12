import os
import json
import asyncio
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
ROLES_CHANNEL_ID = 1515064020573487135
DATA_FILE = "autorole.json"

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

bot = commands.Bot(command_prefix='.', intents=intents, help_command=None)
EMBED_COLOR = 0x2b2d31

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return {int(k): v for k, v in json.load(f).items()}
        except Exception: return {}
    return {}

def save_data():
    with open(DATA_FILE, "w") as f: json.dump(autorole_database, f)

autorole_database = load_data()

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
    # Automatyczne czyszczenie triggera (komendy użytkownika)
    try: await ctx.message.delete()
    except discord.Forbidden: pass

    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        try: role = await ctx.guild.create_role(name=role_name, color=color, mentionable=False)
        except discord.Forbidden: 
            msg = await ctx.send("❌ I need 'Manage Roles' permission.")
            return await asyncio.sleep(5) or await msg.delete()

    if role in ctx.author.roles:
        await ctx.author.remove_roles(role)
        embed = discord.Embed(description=f"✨ {ctx.author.mention}, removed {role.mention} role.", color=EMBED_COLOR)
    else:
        await ctx.author.add_roles(role)
        embed = discord.Embed(description=f"✨ {ctx.author.mention}, assigned {role.mention} role.", color=EMBED_COLOR)
    
    # Wysyłanie i automatyczne kasowanie odpowiedzi po 5 sekundach
    await ctx.send(embed=embed, delete_after=5)

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
async def on_member_join(member):
    role_id = autorole_database.get(member.guild.id)
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            try: await member.add_roles(role)
            except discord.Forbidden: pass

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
    if ctx.author.id != TARGET_USER_ID: return
    embed = discord.Embed(title="🎭 Available Self-Roles", description="Use these commands to toggle your notification pings:", color=EMBED_COLOR)
    embed.add_field(name="`.updates`", value="Toggle the `📢┃Updates` role.", inline=True)
    embed.add_field(name="`.news`", value="Toggle the `📢┃News` role.", inline=True)
    await ctx.send(embed=embed)

@bot.command(name='updates')
async def updates_cmd(ctx):
    if ctx.channel.id != ROLES_CHANNEL_ID and ctx.author.id != TARGET_USER_ID:
        return await ctx.send(f"❌ You can only use this command in <#{ROLES_CHANNEL_ID}>", delete_after=5)
    await toggle_role(ctx, "📢┃Updates", discord.Color.blue())

@bot.command(name='news')
async def news_cmd(ctx):
    if ctx.channel.id != ROLES_CHANNEL_ID and ctx.author.id != TARGET_USER_ID:
        return await ctx.send(f"❌ You can only use this command in <#{ROLES_CHANNEL_ID}>", delete_after=5)
    await toggle_role(ctx, "📢┃News", discord.Color.gold())

@bot.group(name="autorole", invoke_without_command=True)
async def autorole(ctx): pass

@autorole.command(name="add")
async def autorole_add(ctx, role: discord.Role):
    if ctx.author.id != TARGET_USER_ID: return
    autorole_database[ctx.guild.id] = role.id
    save_data()
    await ctx.send(embed=discord.Embed(description=f"✅ Autorole set to {role.mention} and saved permanently.", color=EMBED_COLOR))

@autorole.command(name="list")
async def autorole_list(ctx):
    if ctx.author.id != TARGET_USER_ID: return
    role_id = autorole_database.get(ctx.guild.id)
    role = ctx.guild.get_role(role_id) if role_id else None
    desc = f"Active persistent autorole: {role.mention}" if role else "No autorole configuration active."
    await ctx.send(embed=discord.Embed(description=desc, color=EMBED_COLOR))

@autorole.command(name="remove")
async def autorole_remove(ctx):
    if ctx.author.id != TARGET_USER_ID: return
    if autorole_database.pop(ctx.guild.id, None):
        save_data()
        await ctx.send(embed=discord.Embed(description="❌ Autorole disabled and database cleared.", color=EMBED_COLOR))

@bot.command(name='list')
async def list_help(ctx):
    if ctx.author.id != TARGET_USER_ID: return
    embed = discord.Embed(title="🛠️ System Core Command List", description="Current operational framework commands:", color=EMBED_COLOR)
    embed.add_field(name="`.list`", value="Displays this core diagnostics list.", inline=False)
    embed.add_field(name="`.roles`", value="Shows all self-assignable public roles.", inline=False)
    embed.add_field(name="`.updates`", value="Toggle the updates ping role.", inline=True)
    embed.add_field(name="`.news`", value="Toggle the news ping role.", inline=True)
    embed.add_field(name="`.autorole add/list/remove`", value="Configure master welcome roles (Owner only).", inline=False)
    await ctx.send(embed=embed)

Thread(target=run_web).start()
bot.run(os.environ.get("DISCORD_TOKEN"))
