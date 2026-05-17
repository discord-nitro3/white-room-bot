import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import asyncio

# --- SUROWY SERWER FLASK ---
app = Flask('')

@app.route('/')
def home():
    return "MP3 Queue Sync: Active"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# --- REPLIKATOR & KOLEJKA MP3 (1v99) ---
intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True  
intents.guilds = True
intents.voice_states = True     

bot = commands.Bot(command_prefix="!", intents=intents)

USER_TO_COPY_ID = 1143856525648076812

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# Słownik do przechowywania kolejek dla różnych serwerów
music_queues = {}

def check_queue(ctx):
    """Funkcja wywoływana automatycznie po zakończeniu utworu"""
    guild_id = ctx.guild.id
    vc = ctx.voice_client

    if guild_id in music_queues and music_queues[guild_id]:
        # Pobieramy następny utwór z kolejki
        next_attachment = music_queues[guild_id].pop(0)
        
        vc.play(
            discord.FFmpegPCMAudio(next_attachment.url, **FFMPEG_OPTIONS), 
            after=lambda e: check_queue(ctx)
        )
        # Wysłanie powiadomienia o automatycznym przejściu dalej
        bot.loop.create_task(ctx.send(f"playing {next_attachment.filename} // FROM QUEUE"))
    else:
        # Jeśli kolejka jest pusta, bot czeka na kanale w ciszy
        print(f"[VOICE] Kolejka pusta na serwerze {guild_id}")

@bot.command()
async def play(ctx):
    if not ctx.author.voice:
        return

    if not ctx.message.attachments:
        await ctx.send("playing nothing // BRAK PLIKU MP3")
        return

    attachment = ctx.message.attachments[0]
    
    if not attachment.content_type or not attachment.content_type.startswith('audio/'):
        await ctx.send("playing nothing // TO NIE JEST PLIK AUDIO")
        return

    voice_channel = ctx.author.voice.channel
    
    if ctx.voice_client is None:
        vc = await voice_channel.connect()
    else:
        vc = ctx.voice_client

    guild_id = ctx.guild.id
    if guild_id not in music_queues:
        music_queues[guild_id] = []

    # Jeśli bot aktualnie coś odtwarza, dodaj plik do kolejki
    if vc.is_playing():
        music_queues[guild_id].append(attachment)
        await ctx.send(f"added to queue // {attachment.filename}")
        print(f"[VOICE] Dodano do kolejki: {attachment.filename}")
    else:
        # Jeśli nic nie gra, odpal od razu
        try:
            vc.play(
                discord.FFmpegPCMAudio(attachment.url, **FFMPEG_OPTIONS), 
                after=lambda e: check_queue(ctx)
            )
            await ctx.send(f"playing {attachment.filename}")
            print(f"[VOICE] Odtwarzanie: {attachment.filename}")
        except Exception as e:
            print(f"[ERROR] Błąd odtwarzania MP3: {e}")

@bot.command()
async def skip(ctx):
    """Pomiń aktualny utwór"""
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()  # Wywołanie .stop() automatycznie uruchomi funkcję check_queue (after=)
        await ctx.send("skipped // POMINIĘTO UTWÓR")
        print("[VOICE] Ręczne pominięcie utworu.")

@bot.command()
async def clear(ctx):
    """Wyczyść kolejkę i rozłącz bota"""
    guild_id = ctx.guild.id
    if guild_id in music_queues:
        music_queues[guild_id].clear()
    
    vc = ctx.voice_client
    if vc:
        await vc.disconnect()
        await ctx.send("queue cleared // SYSTEM ROZŁĄCZONY")
        print("[VOICE] Kolejka wyczyszczona, bot opuścił kanał.")

@bot.event
async def on_presence_update(before, after):
    # Klonowanie statusu kropki działa niezależnie w tle
    if after.id == USER_TO_COPY_ID:
        await bot.change_presence(status=after.status)

@bot.event
async def on_ready():
    for guild in bot.guilds:
        member = guild.get_member(USER_TO_COPY_ID)
        if member:
            await bot.change_presence(status=member.status)
            break
    print(f"[SYSTEM] Protokół 1v99 załadowany. Replikacja + System Kolejkowania aktywny.")

# --- ROZRUCH ---
keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))
