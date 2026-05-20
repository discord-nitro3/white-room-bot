import os
import asyncio
import sys
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands
import yt_dlp

# --- LIGHTWEIGHT & STABLE FFMPEG LOADER ---
try:
    import ffdl
    if not os.path.exists("ffmpeg") and not os.path.exists("ffmpeg.exe"):
        print("Downloading stable FFmpeg binary...")
        ffdl.main(["-n"])
    FFMPEG_EXE = "./ffmpeg" if os.name != "nt" else "ffmpeg.exe"
    print(f"FFmpeg ready at: {FFMPEG_EXE}")
except Exception as e:
    print(f"FFmpeg loader alert: {e}. Using system fallback.")
    FFMPEG_EXE = "ffmpeg"

# --- LIGHTWEIGHT WEB SERVER FOR RENDER UPTIME ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running perfectly!"

def run_web():
    app.run(host='0.0.0.0', port=10000)

# --- BOT CONFIGURATION ---
TARGET_USER_ID = 1143856525648076812

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'scsearch',
}

# Volume set to 1.5 (150% boost) for powerful audio output
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=1.5"',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
queue = []

async def sync_activity(guild=None):
    member = guild.get_member(TARGET_USER_ID) if guild else None
    if not member:
        for g in bot.guilds:
            member = g.get_member(TARGET_USER_ID)
            if member: break

    if member and member.status != discord.Status.offline:
        await bot.change_presence(status=discord.Status.dnd, activity=member.activity)
    else:
        await bot.change_presence(status=discord.Status.dnd, activity=None)

async def update_status(guild):
    if guild.voice_client and guild.voice_client.is_playing() and queue:
        track_title = queue[0].get('title', 'Unknown Track')
        await bot.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(type=discord.ActivityType.listening, name=track_title)
        )
    else:
        await sync_activity(guild)

def play_next(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()

    if len(queue) > 1:
        queue.pop(0)
        next_track = queue[0]
        
        ctx.voice_client.play(
            discord.FFmpegPCMAudio(next_track['url'], executable=FFMPEG_EXE, **FFMPEG_OPTIONS), 
            after=lambda e: play_next(ctx)
        )
        
        embed = discord.Embed(title="Now Playing", description=f"**{next_track['title']}**", color=0xff5500)
        if next_track['thumbnail']:
            embed.set_thumbnail(url=next_track['thumbnail'])
        embed.set_footer(text="Streaming from SoundCloud")
        
        bot.loop.create_task(ctx.send(embed=embed))
        bot.loop.create_task(update_status(ctx.guild))
    else:
        if queue: queue.pop(0)
        bot.loop.create_task(update_status(ctx.guild))

@bot.event
async def on_ready():
    print(f'Logged in successfully as {bot.user.name}')
    await sync_activity()

@bot.event
async def on_presence_update(before, after):
    if after.id == TARGET_USER_ID:
        if after.guild.voice_client and after.guild.voice_client.is_playing():
            return
        await sync_activity(after.guild)

@bot.event
async def on_voice_state_update(member, before, after):
    vc = member.guild.voice_client
    if vc and vc.channel and len([m for m in vc.channel.members if not m.bot]) == 0:
        queue.clear()
        if vc.is_playing(): vc.stop()
        await vc.disconnect()
        await sync_activity(member.guild)

# --- MUSIC COMMANDS (ENGLISH INTERFACE) ---

@bot.command(name='play')
async def play(ctx, *, search: str = None):
    if not search:
        return await ctx.send(embed=discord.Embed(description="❌ Please provide a song name or a SoundCloud link!", color=0xff0000))

    if not ctx.author.voice:
        return await ctx.send(embed=discord.Embed(description="❌ You must join a voice channel first!", color=0xff0000))

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    async with ctx.typing():
        try:
            info = ytdl.extract_info(search, download=False)
            if 'entries' in info: info = info['entries'][0]
            
            track_data = {
                'url': info['url'],
                'title': info.get('title', 'Unknown Track'),
                'thumbnail': info.get('thumbnail') or info.get('uploader_avatar')
            }
        except Exception as e:
            return await ctx.send(embed=discord.Embed(description=f"❌ SoundCloud error: {e}", color=0xff0000))

    queue.append(track_data)

    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        embed = discord.Embed(title="Added to Queue", description=f"**{track_data['title']}**", color=0x00ff00)
        if track_data['thumbnail']: embed.set_thumbnail(url=track_data['thumbnail'])
        await ctx.send(embed=embed)
    else:
        ctx.voice_client.play(discord.FFmpegPCMAudio(track_data['url'], executable=FFMPEG_EXE, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
        embed = discord.Embed(title="Now Playing", description=f"**{track_data['title']}**", color=0xff5500)
        if track_data['thumbnail']: embed.set_thumbnail(url=track_data['thumbnail'])
        embed.set_footer(text="Streaming from SoundCloud")
        await ctx.send(embed=embed)
        await update_status(ctx.guild)

@bot.command(name='skip')
async def skip(ctx):
    if not ctx.voice_client or not ctx.voice_client.is_playing():
        return await ctx.send(embed=discord.Embed(description="❌ There is no track currently playing.", color=0xff0000))
    ctx.voice_client.stop()
    await ctx.send(embed=discord.Embed(description="⏭️ Track skipped successfully.", color=0xffff00))

@bot.command(name='pause')
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send(embed=discord.Embed(description="⏸️ Music paused.", color=0xffff00))
    else:
        await ctx.send(embed=discord.Embed(description="❌ Nothing is playing right now.", color=0xff0000))

@bot.command(name='resume')
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send(embed=discord.Embed(description="▶️ Music resumed.", color=0x00ff00))
    else:
        await ctx.send(embed=discord.Embed(description="❌ Music is not paused.", color=0xff0000))

@bot.command(name='queue')
async def view_queue(ctx):
    if not queue:
        return await ctx.send(embed=discord.Embed(description="📁 The queue is currently empty.", color=0x7289da))
    
    description = ""
    for i, track in enumerate(queue):
        prefix = "🔥 Now Playing:" if i == 0 else f"`{i}`."
        description += f"{prefix} **{track['title']}**\n"
        
    await ctx.send(embed=discord.Embed(title="🎵 Current Audio Queue", description=description, color=0x7289da))

@bot.command(name='clear')
async def clear(ctx):
    queue.clear()
    if ctx.voice_client:
        if ctx.voice_client.is_playing(): ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send(embed=discord.Embed(description="⏹️ Queue cleared and disconnected.", color=0xff0000))
    else:
        await ctx.send(embed=discord.Embed(description="❌ Bot is not connected to a voice channel.", color=0xff0000))
    await sync_activity(ctx.guild)

@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(title="🎵 Music Bot Controls", description="Stream seamless, high-volume sound directly from SoundCloud.", color=0x7289da)
    embed.add_field(name="`!play <search/URL>`", value="Plays or queues a track from SoundCloud.", inline=False)
    embed.add_field(name="`!skip`", value="Skips the current music track.", inline=False)
    embed.add_field(name="`!pause` / `!resume`", value="Pauses or resumes the audio player.", inline=False)
    embed.add_field(name="`!queue`", value="Shows all upcoming tracks in the list.", inline=False)
    embed.add_field(name="`!clear`", value="Flushes the queue and leaves the channel.", inline=False)
    embed.set_footer(text="Audio amplification (150% Volume) enabled natively.")
    await ctx.send(embed=embed)

Thread(target=run_web).start()
bot.run(os.environ.get("DISCORD_TOKEN"))
