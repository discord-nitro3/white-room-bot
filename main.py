```python
import os
import asyncio
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import yt_dlp as youtube_dl

# --- SERWER KEEP-ALIVE (Utrzymanie hostingu Render) ---
app = Flask('')

@app.route('/')
def home():
    return "1v99 Music Core: Active & Stable"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# --- PROFESSIONAL YTDL CONFIGURATION (SoundCloud & YT Stability) ---
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'force-ipv4': True,
    'cachedir': False
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]

        if data is None:
            return None

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# --- DISCORD SYSTEM CONFIGURATION ---
intents = discord.Intents.default()
intents.message_content = True  
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None, case_insensitive=True)

# --- BAZA UTWORÓW (Szybkie aliasy tekstowe do odtwarzania) ---
TRACK_MAPPING = {
    "laced up": "https://soundcloud.com/rxssy/laced-up-w-burgos",
    "she not smilin": "https://soundcloud.com/rxssy/she-not-smilin-while-im-winnin",
    "gdzie moj dom": "https://soundcloud.com/youngmulti/gdzie-moj-dom",
    "crazy for you": "https://soundcloud.com/rebzyyx/im-so-crazy-for-youuu"
}

# --- STALE ZDEFINIOWANY STATUS (DND) ---
@bot.event
async def on_ready():
    # Stały status Do Not Disturb (Nie przeszkadzać)
    await bot.change_presence(
        status=discord.Status.dnd, 
        activity=discord.Game(name="!help | 1v99 Matrix")
    )
    print("[SYSTEM] 1v99 Professional Music Core deployed on host.")

# --- KOMENDY DISCORD (Czysty Profesjonalizm) ---

@bot.command(name="play", aliases=["p"])
async def cmd_play(ctx, *, search: str):
    """Odtwarzanie utworów z SoundCloud / YouTube lub słów kluczowych"""
    if not ctx.author.voice:
        embed = discord.Embed(title="❌ BŁĄD SYSTEMU", description="Musisz najpierw dołączyć do kanału głosowego.", color=0xff0000)
        return await ctx.send(embed=embed)

    # Sprawdzenie uprawnień do dołączenia i mówienia
    permissions = ctx.author.voice.channel.permissions_for(ctx.me)
    if not permissions.connect or not permissions.speak:
        embed = discord.Embed(title="❌ BRAK UPRAWNIEŃ", description="Nie mam uprawnień do połączenia lub mówienia na tym kanale.", color=0xff0000)
        return await ctx.send(embed=embed)

    # Automatyczne mapowanie skrótów z bazy danych
    query = search.lower().strip()
    if query in TRACK_MAPPING:
        url_to_play = TRACK_MAPPING[query]
    else:
        url_to_play = search

    async with ctx.typing():
        # Dołączenie do kanału, jeśli bot jeszcze tam nie jest
        if ctx.voice_client is None:
            await ctx.author.voice.channel.connect()
        elif ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.voice_client.move_to(ctx.author.voice.channel)

        try:
            player = await YTDLSource.from_url(url_to_play, loop=bot.loop, stream=True)
            if player is None:
                raise Exception("Nie znaleziono strumienia.")
                
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()

            ctx.voice_client.play(player, after=lambda e: print(f'Odtwarzanie zakończone: {e}') if e else None)
            
            embed = discord.Embed(
                title="🔮 REPRODUKCJA AUDIO",
                description=f"**Odtwarzanie:** `{player.title}`",
                color=0x4d0099
            )
            embed.set_footer(text="Protokół: 1v99 Audio Engine")
            await ctx.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="⚠️ PROCES PRZERWANY",
                description="Nie udało się załadować utworu. Upewnij się, że link SoundCloud/YT jest publiczny.",
                color=0xffaa00
            )
            await ctx.send(embed=embed)

@bot.command(name="stop", aliases=["leave", "dc"])
async def cmd_stop(ctx):
    """Zatrzymanie muzyki i opuszczenie kanału"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        embed = discord.Embed(description="🔌 Rozłączono z sektorem głosowym.", color=0x000000)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(description="Bot nie jest połączony z żadnym kanałem.", color=0x333333)
        await ctx.send(embed=embed)

@bot.command(name="help", aliases=["h"])
async def cmd_help(ctx):
    """Profesjonalny panel komend muzycznych"""
    embed = discord.Embed(
        title="🌌 1v99 MUSIC CORE INTERFACE",
        description="Surowy, stabilny system odtwarzania audio.",
        color=0x000000
    )
    embed.add_field(
        name="🎛️ SYSTEM COMMANDS",
        value=(
            "`!play [link/nazwa]` - Odtwarza utwór z SoundCloud, YT lub bazy\n"
            "`!stop` - Wyłącza odtwarzacz i czyści połączenie głosowe\n"
            "`!help` - Wyświetla tę konsolę"
        ),
        inline=False
    )
    embed.add_field(
        name="⚡ SZYBKIE UTWORY (Wpisz zamiast linku)",
        value="`laced up` | `she not smilin` | `gdzie moj dom` | `crazy for you`",
        inline=False
    )
    embed.set_footer(text="Status: dnd // Tryb: Stały")
    await ctx.send(embed=embed)

# --- PROFESSIONAL ERROR HANDLING (Zabezpieczenie przed surowymi błędami) ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Ignoruj nieistniejące komendy w ciszy
    
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="❌ SYSTEM LOCK", description="Nie posiadasz wymaganych uprawnień administratora do tej operacji.", color=0xff0000)
        await ctx.send(embed=embed)
        
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(title="⚠️ BŁĄD SKŁADNI", description=f"Komenda wymaga podania argumentu. Wpisz np: `!play laced up`", color=0xffaa00)
        await ctx.send(embed=embed)
        
    else:
        # Logowanie rzadkich błędów w estetyczny sposób
        print(f"[BŁĄD KOMENDY]: {error}")

# Inicjalizacja hostingu i uruchomienie bota za pomocą zmiennej środowiskowej
keep_alive()
bot.run(os.environ.get("DISCORD_TOKEN"))

```
