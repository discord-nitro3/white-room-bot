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
intents.presences = True    # Kluczowe do czytania statusów (DND, aktywności)
intents.members = True      # Kluczowe do namierzania celu na serwerze
bot = discord.Client(intents=intents)

# Parametry systemowe
TARGET_CHANNEL_ID = 1505627516898119762
USER_TO_COPY_ID = 1147572718162235472  # ID osoby, której status i grę klonujemy

@tasks.loop(seconds=30)
async def impuls_synchroniczny():
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel:
        await channel.send("1v99 // CYKLICZNY IMPULS SYNCHRONIZACYHNY")

@bot.event
async def on_presence_update(before, after):
    # Monitorowanie celu i natychmiastowe klonowanie statusu/aktywności w locie
    if after.id == USER_TO_COPY_ID:
        await bot.change_presence(
            status=after.status,
            activity=after.activity
        )

@bot.event
async def on_ready():
    # Surowy meldunek na nowym kanale logowania
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel:
        await channel.send("1v99 // STATUS: LISTENING")
    
    # Inicjalne pobranie statusu celu zaraz po rozruchu bota
    for guild in bot.guilds:
        member = guild.get_member(USER_TO_COPY_ID)
        if member:
            await bot.change_presence(status=member.status, activity=member.activity)
            break
        
    print(f"[SYSTEM] Wdrożono protokół 1v99 jako {bot.user}")
    if not impuls_synchroniczny.is_running():
        impuls_synchroniczny.start()

# --- START UP ---
keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))
