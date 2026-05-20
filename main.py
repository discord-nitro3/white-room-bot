import os
import asyncio
import sys
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands
import yt_dlp

# --- AUTOMATYCZNY, STABILNY POZYSKIWACZ FFMPEG ---
try:
    import ffdl
    if not os.path.exists("ffmpeg") and not os.path.exists("ffmpeg.exe"):
        print("Pobieranie stabilnego FFmpeg dla bezpiecznego streamingu...")
        ffdl.main(["-n"])
    FFMPEG_EXE = "./ffmpeg" if os.name != "nt" else "ffmpeg.exe"
    print(f"Sukces! FFmpeg przygotowany pod ścieżką: {FFMPEG_EXE}")
except Exception as e:
    print(f"Problem z inicjalizacją ffdl: {e}. Próba użycia domyślnego aliasu.")
    FFMPEG_EXE = "ffmpeg"

# --- WEB SERVER FOR RENDER UPTIME ---
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

# PODBICIĘ GŁOŚNOŚCI (volume=1.5 oznacza 150% głośności bazowej, bez przesteru)
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=1.5"',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
queue = []

async def sync_activity_from_target(guild=None):
    member = None
    if guild:
        member = guild.get_member(TARGET_USER_ID)
    else:
        for g in bot.guilds:
            member = g.get_member(TARGET_USER_ID)
            if member:
                break

    if member and member.status != discord.Status.offline:
        target_activity = member.activity if member.activity else None
        await bot.change_presence(status=discord.Status.dnd, activity=target_activity)
    else:
        await bot.change_presence(status=discord.Status.dnd, activity=None)

async def update_bot_status(guild):
    if guild.voice_client and guild.voice_client.is_playing() and queue:
        current_track = queue[0]
        track_title = current_track.get('title', 'Unknown Track')
        await bot.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(type=discord.ActivityType.listening, name=track_title)
        )
    else:
        await sync_activity_from_target(guild)

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
        bot.loop.create_task(update_bot_status(ctx.guild))
    else:
        if queue:
            queue.pop(0)
        bot.loop.create_task(update_bot_status(ctx.guild))

@bot.event
async def on_ready():
    print(f'Logged in successfully as {bot.user.name}')
    await sync_activity_from_target()

@bot.event
async def on_presence_update(before, after):
    if after.id == TARGET_USER_ID:
        for guild in bot.guilds:
            vc = guild.voice_client
            if vc and vc.is_playing():
                return
        await sync_activity_from_target(after.guild)

@bot.event
async def on_voice_state_update(member, before, after):
    voice_client = member.guild.voice_client
    if voice_client and voice_client.channel:
        non_bot_members = [m for m in voice_client.channel.members if not m.bot]
        if len(non_bot_members) == 0:
            queue.clear()
            if voice_client.is_playing():
                voice_client.stop()
            await voice_client.disconnect()
            await sync_activity_from_target(member.guild)

# --- MUSIC BOT COMMANDS ---

@bot.command(name='play')
async def play(ctx, *, search: str = None):
    if not search:
        embed = discord.Embed(description="❌ Please provide a song name or a SoundCloud link!", color=0xff0000)
        return await ctx.send(embed=embed)

    if not ctx.author.voice:
        embed = discord.Embed(description="❌ You must join a voice channel first before using this command!", color=0xff0000)
        return await ctx.send(embed=embed)

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    async with ctx.typing():
        try:
            info = ytdl.extract_info(search, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            
            artwork = info.get('thumbnail') or info.get('uploader_avatar')
            
            track_data = {
                'url': info['url'],
                'original_url': info.get('webpage_url', search),
                'title': info.get('title', 'Unknown Track'),
                'thumbnail': artwork,
                'duration': info.get('duration', 0)
            }
        except Exception as e:
            embed = discord.Embed(description=f"❌ Error extracting data from SoundCloud: {e}", color=0xff0000)
            return await ctx.send(embed=embed)

    queue.append(track_data)

    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        embed = discord.Embed(title="Added to Queue", description=f"**{track_data['title']}**", color=0x00ff00)
        if track_data['thumbnail']:
            embed.set_thumbnail(url=track_data['thumbnail'])
        embed.set_footer(text="Positioned safely in the queue.")
        await ctx.send(embed=embed)
    else:
        ctx.voice_client.play(
            discord.FFmpegPCMAudio(track_data['url'], executable=FFMPEG_EXE, **FFMPEG_OPTIONS), 
            after=lambda e: play_next(ctx)
        )
        embed = discord.Embed(title="Now Playing", description=f"**{track_data['title']}**", color=0xff5500)
        if track_data['thumbnail']:
            embed.set_thumbnail(url=track_data['thumbnail'])
        embed.set_footer(text="Streaming from SoundCloud")
        
        await ctx.send(embed=embed)
        await update_bot_status(ctx.guild)

@bot.command(name='skip')
async def skip(ctx):
    if not ctx.voice_client or not ctx.voice_client.is_playing():
        embed = discord.Embed(description="❌ There is no music track currently playing to skip.", color=0xff0000)
        return await ctx.send(embed=embed)
        
    ctx.voice_client.stop()
    embed = discord.Embed(description="⏭️ Current track skipped successfully.", color=0xffff00)
    await ctx.send(embed=embed)

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
        
    embed = discord.Embed(title="🎵 Current Audio Queue", description=description, color=0x7289da)
    await ctx.send(embed=embed)

@bot.command(name='clear')
async def clear(ctx):
    queue.clear()
    if ctx.voice_client:
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        embed = discord.Embed(description="⏹️ Queue flushed. Cleaned up and disconnected from the voice channel.", color=0xff0000)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(description="❌ The bot is not connected to any voice channel active.", color=0xff0000)
        await ctx.send(embed=embed)
    await sync_activity_from_target(ctx.guild)

@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(title="🎵 Professional Music Bot Controls", description="Stream top tier sound directly from SoundCloud seamlessly.", color=0x7289da)
    embed.add_field(name="`!play <wyszukiwanie/URL>`", value="Odtwarza utwór ze SoundCloud lub dodaje do kolejki.", inline=False)
    embed.add_field(name="`!skip`", value="Pomiń aktualnie grany utwór.", inline=False)
    embed.add_field(name="`!pause`", value="Zatrzymaj odtwarzanie muzyki.", inline=True)
    embed.add_field(name="`!resume`", value="Wznów zatrzymaną muzykę.", inline=True)
    embed.add_field(name="`!queue`", value="Zobacz listę nadchodzących utworów.", inline=False)
    embed.add_field(name="`!clear`", value="Wyczyść kolejkę i wyjdź z kanału.", inline=False)
    embed.set_footer(text="Podbicie głośności (150%) włączone na stałe.")
    await ctx.send(embed=embed)

Thread(target=run_web).start()
bot.run(os.environ.get("DISCORD_TOKEN"))
