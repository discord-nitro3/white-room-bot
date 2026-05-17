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
    return "SYSTEM ONLINE"

def run():
    app.run(host='0.0.0.0', port=8080)

def takt_systemowy():
    t = Thread(target=run)
    t.start()

# --- KONFIGURACJA DISCORDA (1v99) ---
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True  # Wymagane do czytania statusów innych osób
intents.members = True    # Wymagane do znalezienia użytkownika na serwerze
bot = discord.Client(intents=intents)

TARGET_CHANNEL_ID = 1505489892174467155
USER_TO_COPY_ID = 1147572718162235472  # Tutaj wpisz ID osoby, której status kopiujesz

@tasks.loop(seconds=30)
async def impuls_synchroniczny():
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel:
        await channel.send("1v99 // CYKLICZNY IMPULS SYNCHRONIZACYJNY")

@bot.event
async def on_presence_update(before, after):
    # Automatyczne kopiowanie statusu i aktywności w locie
    if after.id == USER_TO_COPY_ID:
        await bot.change_presence(
            status=after.status,
            activity=after.activity
        )

@bot.event
async def on_ready():
    # Log na wybranym kanale przy starcie bota
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel:
        await channel.send("1v99 // STATUS: LISTENING")
    
    # Próba skopiowania statusu od razu po starcie bota
    for guild in bot.guilds:
        member = guild.get_member(USER_TO_COPY_ID)
        if member:
            await bot.change_presence(status=member.status, activity=member.activity)
            break
        
    print(f"[SYSTEM] Zalogowano jako {bot.user}")
    if not impuls_synchroniczny.is_running():
        impuls_synchroniczny.start()

# --- START UP ---
takt_systemowy()
bot.run(os.environ.get('DISCORD_TOKEN'))
