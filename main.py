import os
import json
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
DATA_FILE = "autorole.json"
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

bot = commands.Bot(command_prefix='.', intents=intents, help_command=None)
EMBED_COLOR = 0x7289da

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

@bot.event
async def on_ready():
    await sync_activity()
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        try: await channel.send(f"<@{TARGET_USER_ID}> online ☕")
        except discord.Forbidden: print("Brak uprawnień do pisania na kanale logów.")

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

@bot.command(name='updates')
async def updates_role(ctx):
    role_name = "📢┃Updates"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        try: role = await ctx.guild.create_role(name=role_name, color=discord.Color.blue(), mentionable=True)
        except discord.Forbidden: return await ctx.send("❌ I need 'Manage Roles' permission to create the role.")
    if role in ctx.author.roles:
        await ctx.author.remove_roles(role)
        await ctx.send(embed=discord.Embed(description=f"🔔 Removed {role.mention}. You won't get update pings.", color=EMBED_COLOR))
    else:
        await ctx.author.add_roles(role)
        await ctx.send(embed=discord.Embed(description=f"🔔 Assigned {role.mention}. You will now get update pings!", color=EMBED_COLOR))

@bot.group(name="autorole", invoke_without_command=True)
@commands.has_permissions(manage_roles=True)
async def autorole(ctx): pass

@autorole.command(name="add")
@commands.has_permissions(manage_roles=True)
async def autorole_add(ctx, role: discord.Role):
    autorole_database[ctx.guild.id] = role.id
    save_data()
    await ctx.send(embed=discord.Embed(description=f"✅ Autorole set to {role.mention} and saved permanently.", color=EMBED_COLOR))

@autorole.command(name="show")
@commands.has_permissions(manage_roles=True)
async def autorole_show(ctx):
    role_id = autorole_database.get(ctx.guild.id)
    role = ctx.guild.get_role(role_id) if role_id else None
    desc = f"Active autorole: {role.mention}" if role else "No autorole set."
    await ctx.send(embed=discord.Embed(description=desc, color=EMBED_COLOR))

@autorole.command(name="remove")
@commands.has_permissions(manage_roles=True)
async def autorole_remove(ctx):
    if autorole_database.pop(ctx.guild.id, None):
        save_data()
        await ctx.send(embed=discord.Embed(description="❌ Autorole disabled and config cleared.", color=EMBED_COLOR))
    else:
        await ctx.send(embed=discord.Embed(description="No active autorole config found.", color=EMBED_COLOR))

@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(title="⚙️ Config Bot Controls", description="System utility framework with deployment notifications.", color=EMBED_COLOR)
    embed.add_field(name="`.updates`", value="Toggle the updates notification ping role.", inline=False)
    embed.add_field(name="`.autorole add/show/remove`", value="Manage automatic welcoming roles.", inline=False)
    await ctx.send(embed=embed)

Thread(target=run_web).start()
bot.run(os.environ.get("DISCORD_TOKEN"))
