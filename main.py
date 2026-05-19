import os
import asyncio
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands
import yt_dlp

# --- SERWER WEB DLA RENDERA ---
# Render wymaga, aby aplikacja nasłuchiwała na porcie HTTP, inaczej zgłosi błąd wdrożenia.
app = Flask('')

@app.route('/')
def home():
    return "Bot gra i trąbi!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- KONFIGURACJA BOTA ---
intents = discord.Intents.default()
intents.message_content = True
# Stały status Do Not Disturb (DND)
bot = commands.Bot(command_prefix='!', intents=intents, status=discord.Status.dnd)

# Konfiguracja yt_dlp dla SoundCloud i streamingu
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'scsearch',  # Domyślne wyszukiwanie na SoundCloud
}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# Kolejka utworów i przechowywanie nazw
queue = []
titles_queue = []

async def update_status(guild):
    """Aktualizuje status bota o obecnie grany utwór."""
    if guild.voice_client and guild.voice_client.is_playing() and titles_queue:
        current_track = titles_queue[0]
        await bot.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(type=discord.ActivityType.listening, name=current_track)
        )
    else:
        await bot.change_presence(status=discord.Status.dnd, activity=None)

def play_next(ctx):
    """Funkcja wywoływana po zakończeniu odtwarzania utworu."""
    if len(queue) > 0:
        url = queue.pop(0)
        titles_queue.pop(0)
        
        ctx.voice_client.play(
            discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), 
            after=lambda e: play_next(ctx)
        )
        # Aktualizacja statusu (uruchamiana w pętli bota)
        bot.loop.create_task(update_status(ctx.guild))
    else:
        bot.loop.create_task(update_status(ctx.guild))

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user.name}')
    await bot.change_presence(status=discord.Status.dnd)

@bot.event
async def on_voice_state_update(member, before, after):
    """Automatyczne wychodzenie, gdy bot zostanie sam na kanale."""
    voice_client = member.guild.voice_client
    if voice_client and voice_client.channel:
        # Liczymy tylko prawdziwych użytkowników (bez botów)
        non_bot_members = [m for m in voice_client.channel.members if not m.bot]
        if len(non_bot_members) == 0:
            # Czyszczenie kolejek przy wyjściu
            queue.clear()
            titles_queue.clear()
            await voice_client.disconnect()
            await bot.change_presence(status=discord.Status.dnd, activity=None)

@bot.command(name='play')
async def play(ctx, *, search: str):
    """Odtwarza utwór z SoundCloud na podstawie linku lub wyszukiwania."""
    if not ctx.author.voice:
        return await ctx.send("Musisz być na kanale głosowym!")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    async with ctx.typing():
        try:
            # Pobranie info z SoundCloud przez yt_dlp
            info = ytdl.extract_info(search, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            
            url = info['url']
            title = info.get('title', 'Nieznany utwór')
        except Exception as e:
            return await ctx.send(f"Błąd podczas szukania na SoundCloud: {e}")

    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        queue.append(url)
        titles_queue.append(title)
        await ctx.send(f"Dodano do kolejki: **{title}**")
    else:
        queue.append(url)
        titles_queue.append(title)
        play_next(ctx)
        await ctx.send(f"Teraz gram: **{title}**")

@bot.command(name='skip')
async def skip(ctx):
    """Pomija obecny utwór."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Utwór pominięty ⏭️")
    else:
        await ctx.send("Nic teraz nie leci.")

@bot.command(name='clear')
async def clear(ctx):
    """Czyści kolejkę i rozłącza bota z kanału."""
    queue.clear()
    titles_queue.clear()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Kolejka wyczyszczona. Bot rozłączony ⏹️")
    else:
        await ctx.send("Bot nie jest połączony z żadnym kanałem.")
    await bot.change_presence(status=discord.Status.dnd, activity=None)

# Uruchomienie serwera HTTP w tle
Thread(target=run_web).start()

# Uruchomienie bota za pomocą zmiennej środowiskowej DISCORD_TOKEN
bot.run(os.environ.get("DISCORD_TOKEN"))
