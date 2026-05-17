import os
import asyncio
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands
import yt_dlp

# --- SUROWY SERWER FLASK ---
app = Flask('')

@app.route('/')
def home():
    return "Status & Voice Sync: Active"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# --- REPLIKATOR & OBSŁUGA AUDIO (1v99) ---
intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True  
intents.guilds = True
intents.voice_states = True     

bot = commands.Bot(command_prefix="!", intents=intents)

USER_TO_COPY_ID = 1143856525648076812

# Maksymalnie zoptymalizowane opcje yt-dlp omijające restrykcje antybotowe serwerowni
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'no_warnings': True,
    'extract_flat': 'in_playlist',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

@bot.command()
async def play(ctx, *, url: str):
    if not ctx.author.voice:
        return

    voice_channel = ctx.author.voice.channel
    
    if ctx.voice_client is None:
        vc = await voice_channel.connect()
    else:
        vc = ctx.voice_client

    try:
        loop = asyncio.get_event_loop()
        # Wyciąganie czystych metadanych strumienia
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        
        if 'entries' in data:
            data = data['entries'][0]
            
        song_url = data['url']
        
        if vc.is_playing():
            vc.stop()
            
        vc.play(discord.FFmpegPCMAudio(song_url, **FFMPEG_OPTIONS))
        print(f"[VOICE] Pomyślnie uruchomiono strumień: {data.get('title', 'Audio')}")
    except Exception as e:
        print(f"[ERROR] Krytyczny błąd odtwarzania strumienia: {e}")

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
    print(f"[SYSTEM] Protokół 1v99 załadowany w całości (Status + Anty-Bot Voice).")

# --- ROZRUCH ---
keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))
