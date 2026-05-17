import os
from flask import Flask
from threading import Thread
import discord

# --- SUROWY SERWER FLASK ---
app = Flask('')

@app.route('/')
def home():
    return "Status Sync: Active"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# --- REPLIKATOR STATUSU (1v99) ---
intents = discord.Intents.default()
intents.presences = True
intents.members = True
bot = discord.Client(intents=intents)

USER_TO_COPY_ID = 1143856525648076812

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
    print(f"[SYSTEM] Replikacja statusu aktywna dla {bot.user}")

# --- ROZRUCH ---
keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))
