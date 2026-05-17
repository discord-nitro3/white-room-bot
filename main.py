import os
import asyncio
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands, tasks

# --- SERWER FLASK (DLA RENDERA) ---
app = Flask('')

@app.route('/')
def home():
    return "System integralny 1v99: Aktywny"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- KONFIGURACJA 1v99 (PEŁNE INTENTY) ---
intents = discord.Intents.all()  # Włączamy pełne intenty dla stabilności cache
bot = commands.Bot(command_prefix="!", intents=intents)

# Parametry docelowe
LOG_CHANNEL_ID = 1505627516898119762
USER_TO_COPY_ID = 1143856525648076812

last_tracked_track = None

async def track_music_rpc(member):
    global last_tracked_track
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        return

    title = None
    author = None
    image_url = None

    # Sprawdzanie aktywności RPC
    for activity in member.activities:
        if isinstance(activity, discord.Spotify):
            title = activity.title
            author = activity.artist
            image_url = activity.album_cover_url
            break
        elif activity.type == discord.ActivityType.listening:
            title = activity.name
            author = getattr(activity, 'details', 'Unknown Artist')
            if hasattr(activity, 'large_image_url'):
                image_url = activity.large_image_url
            break

    if title and author:
        current_track_identifier = f"{title} - {author}"
        
        if current_track_identifier != last_tracked_track:
            last_tracked_track = current_track_identifier
            content = f"Currently Listening to {title} - {author}"
            
            if image_url:
                embed = discord.Embed(color=0x000000)
                embed.set_image(url=image_url)
                await channel.send(content=content, embed=embed)
            else:
                await channel.send(content=content)

@tasks.loop(seconds=30)
async def impuls_synchroniczny():
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send("1v99 // CYKLICZNY IMPULS SYNCHRONIZACYJNY")

@bot.event
async def on_presence_update(before, after):
    if after.id == USER_TO_COPY_ID:
        # Klonowanie statusu i aktywności 1:1
        await bot.change_presence(
            status=after.status,
            activity=after.activity
        )
        # Analiza i wysyłka RPC
        await track_music_rpc(after)

@bot.event
async def on_ready():
    # Meldunek startowy na nowym kanale
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send("1v99 // STATUS: LISTENING")
    
    # Wymuszenie pierwszej synchronizacji z pamięci podręcznej serwera
    for guild in bot.guilds:
        member = guild.get_member(USER_TO_COPY_ID)
        if member:
            await bot.change_presence(status=member.status, activity=member.activity)
            await track_music_rpc(member)
            break
        
    print(f"[SYSTEM] Wdrożono protokół 1v99. Klonowanie i nasłuchiwanie aktywne.")
    if not impuls_synchroniczny.is_running():
        impuls_synchroniczny.start()

# --- ROZRUCH SYSTEMU ---
keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))
