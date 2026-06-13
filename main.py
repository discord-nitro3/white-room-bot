import os
import threading
import json
import asyncio
import re
import random
import datetime
from flask import Flask
import discord
from discord.ext import commands, tasks

app = Flask('')
@app.route('/')
def home(): return "Anime Girl Core Status: Operational"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
threading.Thread(target=run_web, daemon=True).start()

TARGET_USER_ID = 1143856525648076812
LOG_CHANNEL_ID = 1515049160561135747
DATA_FILE = "autorole.json"

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

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
EMBED_COLOR = discord.Color(0x2b2d31)

def add_professional_footer(embed, ctx):
    embed.set_footer(text="© 2026 koji_505 | Beta v0.9.3 | Req: koji_505", icon_url=ctx.author.display_avatar.url)
    return embed

def parse_duration(time_str):
    time_regex = re.compile(r'(?P<value>\d+)(?P<unit>[smhd])')
    matches = time_regex.match(time_str.lower())
    if not matches: return None
    group = matches.groupdict()
    val = int(group['value'])
    unit = group['unit']
    if unit == 's': return val
    if unit == 'm': return val * 60
    if unit == 'h': return val * 3600
    if unit == 'd': return val * 86400
    return None

@tasks.loop(minutes=1)
async def update_presence():
    total = sum(g.member_count for g in bot.guilds)
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name=f"{total} members across {len(bot.guilds)} servers"))

@bot.event
async def on_ready():
    print("========================================")
    print(f"Logged in as: {bot.user.name} ({bot.user.id})")
    print("Status: Operational | Beta Phase")
    print("========================================")
    update_presence.start()
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        try: await channel.send(f"<@{TARGET_USER_ID}> online ☕")
        except discord.Forbidden: pass

@bot.event
async def on_member_join(member):
    role_id = autorole_database.get(member.guild.id)
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            try: await member.add_roles(role)
            except discord.Forbidden: pass

@bot.group(name="autorole", invoke_without_command=True)
@commands.has_permissions(manage_roles=True)
async def autorole(ctx):
    embed = discord.Embed(title="⚙️ Autorole Subcommands", description="Available administrative tools:\n`!autorole add @role` - Set automatic role.\n`!autorole list` - Show current configuration.\n`!autorole remove` - Disable framework.", color=EMBED_COLOR)
    await ctx.send(embed=add_professional_footer(embed, ctx))

@autorole.command(name="add")
@commands.has_permissions(manage_roles=True)
async def autorole_add(ctx, role: discord.Role):
    autorole_database[ctx.guild.id] = role.id
    save_data()
    embed = discord.Embed(title="✅ Autorole Configured", description=f"New members will now automatically receive the {role.mention} role.", color=EMBED_COLOR)
    await ctx.send(embed=add_professional_footer(embed, ctx))

@autorole.command(name="list")
@commands.has_permissions(manage_roles=True)
async def autorole_list(ctx):
    role_id = autorole_database.get(ctx.guild.id)
    role = ctx.guild.get_role(role_id) if role_id else None
    desc = f"Current active autorole: {role.mention}" if role else "No autorole configuration detected for this server."
    embed = discord.Embed(title="📊 Autorole Status", description=desc, color=EMBED_COLOR)
    await ctx.send(embed=add_professional_footer(embed, ctx))

@autorole.command(name="remove")
@commands.has_permissions(manage_roles=True)
async def autorole_remove(ctx):
    if autorole_database.pop(ctx.guild.id, None):
        save_data()
        desc = "Autorole framework successfully disabled."
    else: desc = "No active autorole configuration found to remove."
    embed = discord.Embed(title="❌ Autorole Disabled", description=desc, color=EMBED_COLOR)
    await ctx.send(embed=add_professional_footer(embed, ctx))

@bot.group(name="gw", invoke_without_command=True)
@commands.has_permissions(manage_messages=True)
async def gw(ctx):
    embed = discord.Embed(title="🎉 Giveaway Subcommands", description="Available promotional tools:\n`!gw create` - Start an interactive giveaway setup framework.", color=EMBED_COLOR)
    await ctx.send(embed=add_professional_footer(embed, ctx))

@gw.command(name="create")
@commands.has_permissions(manage_messages=True)
async def gw_create(ctx):
    # Usuwanie samej komendy początkowej !gw create
    try: await ctx.message.delete()
    except discord.Forbidden: pass

    def check(m): return m.author == ctx.author and m.channel == ctx.channel

    try:
        q1 = await ctx.send("⏳ **[1/3]** Enter giveaway duration (e.g., `10s`, `5m`, `2h`, `1d`):")
        msg1 = await bot.wait_for('message', check=check, timeout=30.0)
        seconds = parse_duration(msg1.content)
        if seconds is None: return await ctx.send("❌ Invalid time format. Action aborted.", delete_after=5)

        q2 = await ctx.send("👥 **[2/3]** Enter number of winners (e.g., `1`, `3`):")
        msg2 = await bot.wait_for('message', check=check, timeout=30.0)
        if not msg2.content.isdigit() or int(msg2.content) <= 0: return await ctx.send("❌ Invalid winners count. Action aborted.", delete_after=5)
        winners_count = int(msg2.content)

        q3 = await ctx.send("🎁 **[3/3]** Enter the giveaway prize:")
        msg3 = await bot.wait_for('message', check=check, timeout=45.0)
        prize = msg3.content

        try:
            await q1.delete(); await msg1.delete(); await q2.delete(); await msg2.delete(); await q3.delete(); await msg3.delete()
        except discord.Forbidden: pass

    except asyncio.TimeoutError:
        return await ctx.send("❌ Setup timed out. Framework aborted.", delete_after=5)

    embed = discord.Embed(title=f"🎉 GIVEAWAY: {prize}", description=f"React with 🎉 to enter!\n\n⏱️ **Duration:** {msg1.content}\n👥 **Winners:** {winners_count}\n👑 **Hosted by:** {ctx.author.mention}", color=EMBED_COLOR)
    embed = add_professional_footer(embed, ctx)
    gw_message = await ctx.send(embed=embed)
    await gw_message.add_reaction("🎉")

    async def run_gw_timer(duration, msg_id, winners, prize_name, host):
        await asyncio.sleep(duration)
        try:
            target_msg = await ctx.channel.fetch_message(msg_id)
            reaction = discord.utils.get(target_msg.reactions, emoji="🎉")
            users = [u async for u in reaction.users() if not u.bot]
            
            if len(users) == 0:
                end_embed = discord.Embed(title=f"🎉 GIVEAWAY ENDED: {prize_name}", description=f"No entries detected. No winners could be chosen.\n\n👑 **Hosted by:** {host.mention}", color=EMBED_COLOR)
                end_embed.set_footer(text="© 2026 koji_505 | Giveaway Closed", icon_url=host.display_avatar.url)
                await target_msg.edit(embed=end_embed)
                return await ctx.send(f"💨 The giveaway for **{prize_name}** ended, but nobody reacted.")

            winners_list = random.sample(users, min(len(users), winners))
            winners_mention = ", ".join([w.mention for w in winners_list])

            end_embed = discord.Embed(title=f"🎉 GIVEAWAY ENDED: {prize_name}", description=f"🏆 **Winners:** {winners_mention}\n👑 **Hosted by:** {host.mention}", color=EMBED_COLOR)
            end_embed.set_footer(text="© 2026 koji_505 | Giveaway Closed", icon_url=host.display_avatar.url)
            await target_msg.edit(embed=end_embed)
            await ctx.send(f"🎊 Congratulations {winners_mention}! You won **{prize_name}**!")
        except Exception: pass

    asyncio.create_task(run_gw_timer(seconds, gw_message.id, winners_count, prize, ctx.author))

@bot.command(name="timeout", aliases=["mute"])
@commands.has_permissions(moderate_members=True)
async def timeout_cmd(ctx, member: discord.Member, duration_str: str, *, reason="No reason provided"):
    seconds = parse_duration(duration_str)
    if not seconds:
        return await ctx.send("❌ Invalid duration format. Use `10m`, `2h`, `1d` etc.", delete_after=5)
    
    td = datetime.timedelta(seconds=seconds)
    try:
        await member.timeout(td, reason=reason)
        embed = discord.Embed(title="⏳ Member Muted (Timeout)", description=f"Successfully put {member.mention} in timeout.", color=EMBED_COLOR)
        embed.add_field(name="Duration", value=f"`{duration_str}`", inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        await ctx.send(embed=add_professional_footer(embed, ctx))
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to timeout this member (Hierarchy issue).")

@bot.command(name="about")
async def about(ctx):
    embed = discord.Embed(title="ℹ️ Anime Girl Core - Application Profile", description=("**Developer & Intellectual Property Owner:** `koji_505`\n\n**Legal Notice & Terms of Use:**\nAll rights reserved. The source code, custom assets, and configuration of this application are the exclusive property of the developer (`koji_505`). Unauthorized duplication, modification, distribution, or reverse-engineering without explicit written consent from the owner is strictly prohibited.\n\n**Development Status:**\nThis application is currently operating under **Beta Phase (v0.9.3)**. Features are subject to change, and active monitoring is enabled."), color=EMBED_COLOR)
    await ctx.send(embed=add_professional_footer(embed, ctx))

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    embed = discord.Embed(title="👢 Member Kicked", description=f"Successfully kicked {member.mention}", color=EMBED_COLOR)
    embed.add_field(name="Reason", value=reason, inline=False)
    await ctx.send(embed=add_professional_footer(embed, ctx))

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    embed = discord.Embed(title="🔨 Member Banned", description=f"Successfully banned {member.mention}", color=EMBED_COLOR)
    embed.add_field(name="Reason", value=reason, inline=False)
    await ctx.send(embed=add_professional_footer(embed, ctx))

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    deleted = await ctx.channel.purge(limit=amount + 1)
    embed = discord.Embed(title="🧹 Chat Purged", description=f"Successfully deleted `{len(deleted)-1}` messages.", color=EMBED_COLOR)
    await ctx.send(embed=add_professional_footer(embed, ctx), delete_after=5)

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 {guild.name} Database Analysis", color=EMBED_COLOR)
    embed.add_field(name="👑 Guild Owner", value=f"{guild.owner.mention} ({guild.owner})", inline=False)
    embed.add_field(name="👥 Total Population", value=f"`{guild.member_count} users`", inline=True)
    embed.add_field(name="🔒 Security Level", value=f"`{guild.verification_level}`", inline=True)
    embed.add_field(name="📅 Creation Date", value=f"`{guild.created_at.strftime('%B %d, %Y')}`", inline=False)
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    await ctx.send(embed=add_professional_footer(embed, ctx))

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    roles = [r.mention for r in member.roles[1:]]
    roles.reverse()
    embed = discord.Embed(title=f"👤 User Dossier: {member.name}", color=EMBED_COLOR)
    embed.add_field(name="Registry ID", value=f"`{member.id}`", inline=True)
    embed.add_field(name="Arrival Date", value=f"`{member.joined_at.strftime('%d/%m/%Y')}`", inline=True)
    embed.add_field(name="Roles Hierarchy", value=" ".join(roles) if roles else "No custom roles assigned", inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=add_professional_footer(embed, ctx))

@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"🖼️ {member.name}'s Avatar Manifest", color=EMBED_COLOR)
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=add_professional_footer(embed, ctx))

@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(title="🤖 Anime Girl Core — Operational Interface", description="Full core command system architecture:", color=EMBED_COLOR)
    embed.add_field(name="⚙️ Configuration Module", value="`!autorole add/list/remove` — Direct server welcome system management.\n`!gw create` — Start an interactive giveaway setup framework.", inline=False)
    embed.add_field(name="🛡️ Moderation Operations", value="`!kick @user <reason>` — Remove user.\n`!ban @user <reason>` — Ban user.\n`!timeout / !mute @user <time> <reason>` — Temporary structural quarantine.\n`!clear <amount>` — Wipe active channel chat log.", inline=False)
    embed.add_field(name="📊 Diagnostics & Registry", value="`!serverinfo` — Structural data analysis.\n`!userinfo @user` — Profile classification dossier.\n`!avatar @user` — Extract explicit profile avatar canvas.\n`!about` — System licensing profile details.", inline=False)
    await ctx.send(embed=add_professional_footer(embed, ctx))

bot.run(os.environ.get("DISCORD_TOKEN"))
        
