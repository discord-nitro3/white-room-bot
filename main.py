import os
import asyncio
from flask import Flask
from threading import Thread
import discord
from discord.ext import tasks

# --- SUROWY SERWER FLASK (DLA RENDERA) ---
app = Flask('')

@app.route('/')
def home():
    return "System integralny 1v99: Aktywny"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- KONFIGURACJA DISCORDA (1v99) ---
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True    # Wymagane do czytania aktywności i RPC
intents.members = True      # Wymagane do namierzania użytkownika w strukturze
bot = discord.Client(intents=intents)

# Parametry systemowe
LOG_CHANNEL_ID = 1505627516898119762
USER_TO_COPY_ID = 1147572718162235472

# Zmienna do zapamiętywania ostatnio zalogowanego utworu (żeby bot nie spamował tym samym)
last_tracked_track = None

@tasks.loop(seconds=30)
async def impuls_synchroniczny():
    # Surowa pętla taktująca 1v99
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send("1v99 // CYKLICZNY IMPULS SYNCHRONIZACYJNY")

async def track_music_rpc(member):
    global last_tracked_track
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        return

    title = None
    author = None
    image_url = None

    # 1. Sprawdzenie natywnego RPC Spotify
    for activity in member.activities:
        if isinstance(activity, discord.Spotify):
            title = activity.title
            author = activity.artist
            image_url = activity.album_cover_url
            break
        
        # 2. Alternatywa: Sprawdzenie niestandardowego RPC (np. PreMid, iTunes, YouTube Music RPC)
        elif activity.type == discord.ActivityType.listening:
            title = activity.name
            author = getattr(activity, 'details', 'Unknown Artist')
            # Próba wyciągnięcia dużej okładki z Rich Presence Assets
            if hasattr(activity, 'large_image_url'):
                image_url = activity.large_image_url
            break

    if title and author:
        current_track_identifier = f"{title} - {author}"
        
        # Jeśli utwór się zmienił, wysyłamy meldunek
        if current_track_identifier != last_tracked_track:
            last_tracked_track = current_track_identifier
            
            # Budowanie surowego komunikatu tekstowego
            content = f"Currently Listening to {title} - {author}"
            
            # Jeśli RPC udostępnia okładkę, dorzucamy ją jako czysty Embed w chłodnym stylu
            if image_url:
                embed = discord.Embed(color=0x000000)
                embed.set_image(url=image_url)
                await channel.send(content=content, embed=embed)
            else:
                await channel.send(content=content)

@bot.event
async def on_presence_update(before, after):
    # Monitorowanie Twojego konta
    if after.id == USER_TO_COPY_ID:
        # KROK 1: Kopiowanie ogólnego statusu (DND/Idle) i profilowej aktywności 1:1 na bota
        await bot.change_presence(
            status=after.status,
            activity=after.activity
        )
        
        # KROK 2: Sprawdzenie Twojego RPC muzycznego i logowanie na wskazany kanał
        await track_music_rpc(after)

@bot.event
async def on_ready():
    # Inicjalny meldunek techniczny
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send("1v99 // STATUS: LISTENING")
    
    # Pierwsza synchronizacja profilu zaraz po restarcie serwera
    for guild in bot.guilds:
        member = guild.get_member(USER_TO_COPY_ID)
        if member:
            await bot.change_presence(status=member.status, activity=member.activity)
            await track_music_rpc(member)
            break
        
    print(f"[SYSTEM] Wdrożono protokół 1v99. Nasłuchiwanie RPC aktywne.")
    if not impuls_synchroniczny.is_running():
        impuls_synchroniczny.start()

# --- URUCHOMIENIE ---
keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))
