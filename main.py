import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import yt_dlp
import asyncio

# --- SUROWY SERWER FLASK ---
app = Flask('')

@app.route('/')
def home():
    return "SoundCloud & Audio Sync: Active"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# --- REPLIKATOR & SILNIK AUDIO (1v99) ---
intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True  
intents.guilds = True
intents.voice_states = True     

bot = commands.Bot(command_prefix="!", intents=intents)

USER_TO_COPY_ID = 1143856525648076812

# CHŁODNA KONFIGURACJA OMIJAJĄCA YOUTUBE (WYMUSZAMY SOUNDCLOUD / BEZPOŚREDNIE LINKI)
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    # Jeśli podasz sam tekst, bot wyszuka go na SoundCloud zamiast na YouTube
    'default_search': 'scsearch', 
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'no_warnings': True,
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
music_queues = {}

def check_queue(ctx):
    guild_id = ctx.guild.id
    vc = ctx.voice_client

    if guild_id in music_queues and music_queues[guild_id]:
        next_track = music_queues[guild_id].pop(0)
        
        vc.play(
            discord.FFmpegPCMAudio(next_track['url'], **FFMPEG_OPTIONS), 
            after=lambda e: check_queue(ctx)
        )
        bot.loop.create_task(ctx.send(f"playing {next_track['title']} // FROM QUEUE"))
    else:
        print(f"[VOICE] Kolejka pusta na serwerze {guild_id}")

@bot.command()
async def play(ctx, *, search: str):
    if not ctx.author.voice:
        return

    voice_channel = ctx.author.voice.channel
    
    if ctx.voice_client is None:
        vc = await voice_channel.connect()
    else:
        vc = ctx.voice_client

    guild_id = ctx.guild.id
    if guild_id not in music_queues:
        music_queues[guild_id] = []

    # Blokada bezpośrednich linków do YouTube, żeby nie triggerować błędów
    if "youtube.com" in search or "youtu.be" in search:
        await ctx.send("system error // YOUTUBE IS BLOCKING THIS SERVER. USE SOUNDCLOUD LINKS OR TEXT SEARCH.")
        return

    await ctx.send("searching...")

    try:
        loop = asyncio.get_event_loop()
        # Wyciąganie danych z pominięciem YouTube
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search, download=False))
        
        if 'entries' in data and data['entries']:
            data = data['entries'][0]
            
        if not data:
            await ctx.send("playing nothing // NO AUDIO FOUND")
            return

        track_info = {
            'url': data['url'],
            'title': data.get('title', 'Unknown Track')
        }

        if vc.is_playing():
            music_queues[guild_id].append(track_info)
            await ctx.send(f"added to queue // {track_info['title']}")
        else:
            vc.play(
                discord.FFmpegPCMAudio(track_info['url'], **FFMPEG_OPTIONS), 
                after=lambda e: check_queue(ctx)
            )
            await ctx.send(f"playing {track_info['title']}")
            
    except Exception as e:
        print(f"[ERROR] Audio engine error: {e}")
        await ctx.send("system error // CANNOT STREAM THIS SOURCE")

@bot.command()
async def skip(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await ctx.send("skipped // POMINIĘTO UTWÓR")

@bot.command()
async def clear(ctx):
    guild_id = ctx.guild.id
    if guild_id in music_queues:
        music_queues[guild_id].clear()
    vc = ctx.voice_client
    if vc:
        await vc.disconnect()
        await ctx.send("queue cleared // SYSTEM ROZŁĄCZONY")

@bot.event
async def on_presence_update(before, after):
    if after.id == USER_TO_COPY_ID:
        await bot.change_presence(status=after.status)

@bot.event
async def on_ready():
    for guild in bot.guilds:
        member = guild.get_member(USER_TO_COPY_ID)
        if member:
            await bot.change_presence(status=member.status)
            break
    print(f"[SYSTEM] Protokół 1v99 aktywny. Silnik SoundCloud załadowany.")

# --- ROZRUCH ---
keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))
