import os
import discord
from discord.ext import commands
from discord.ui import Button, View
from flask import Flask
from threading import Thread
import yt_dlp
import asyncio

# --- SERWER FLASK (Keep-Alive dla hostingu) ---
app = Flask('')

@app.route('/')
def home():
    # Prosty endpoint sprawdzający stan działania bota
    return "1v98 Music Core: Active & Optimized"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    # Uruchomienie serwera w osobnym wątku
    Thread(target=run).start()

# --- KONFIGURACJA BOTA ---
intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True  
intents.guilds = True
intents.voice_states = True     

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Konfiguracja replikacji obecności
USER_TO_COPY_ID = 1143856525648076812
current_user_status = discord.Status.online

# Zaawansowane opcje maskowania sieciowego dla yt-dlp
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'scsearch', 
    'nocheckcertificate': True,
    'ignoreerrors': False,  # Pozwala na prawidłowe przechwytywanie wyjątków do logów
    'no_warnings': True,
    # Maskujemy bota jako popularną przeglądarkę, aby SoundCloud nie blokował połączeń z hostingu
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pl,en-US;en;q=0.5',
    }
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
music_queues = {}

async def update_bot_presence(track_title=None):
    """Aktualizuje status bota kopiując status użytkownika oraz dodając aktywność"""
    global current_user_status
    activity = discord.Game(name=f"Muzyka: {track_title}") if track_title else None
    await bot.change_presence(status=current_user_status, activity=activity)

def format_duration(seconds):
    """Konwertuje sekundy na czytelny format MM:SS"""
    if not seconds:
        return "Strumień na żywo"
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def create_music_embed(track_info, status="Odtwarzanie"):
    """Tworzy profesjonalny, ciemny panel informacyjny o utworze"""
    embed = discord.Embed(
        title=track_info['title'],
        url=track_info['original_url'],
        color=0x000000  # Czysta, głęboka czerń
    )
    embed.set_author(name=status, icon_url=bot.user.avatar.url if bot.user.avatar else None)
    embed.add_field(name="Autor", value=track_info['uploader'], inline=True)
    embed.add_field(name="Czas trwania", value=format_duration(track_info['duration']), inline=True)
    embed.add_field(name="Źródło", value=track_info['extractor'], inline=True)
    
    if track_info['thumbnail']:
        embed.set_thumbnail(url=track_info['thumbnail'])
        
    embed.set_footer(text="1v98 System Muzyczny", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    return embed

# --- INTERAKTYWNY PANEL STEROWANIA (PRZYCISKI) ---
class InteractiveControlView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)  # Przyciski nigdy nie wygasają
        self.ctx = ctx

    @discord.ui.button(label="Pauza / Wznów ⏸️", style=discord.ButtonStyle.secondary, custom_id="btn_pause_resume")
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.response.send_message("Bot nie jest połączony z kanałem głosowym.", ephemeral=True)
        
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("Odtwarzanie zostało wstrzymane.", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("Odtwarzanie zostało wznowione.", ephemeral=True)
        else:
            await interaction.response.send_message("Aktualnie nic nie jest odtwarzane.", ephemeral=True)

    @discord.ui.button(label="Pomiń utwór ⏭️", style=discord.ButtonStyle.primary, custom_id="btn_skip")
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.ctx.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("Utwór został pominięty.", ephemeral=True)
        else:
            await interaction.response.send_message("Brak utworu do pominięcia.", ephemeral=True)

    @discord.ui.button(label="Rozłącz ⏹️", style=discord.ButtonStyle.danger, custom_id="btn_stop")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.ctx.guild.id
        if guild_id in music_queues:
            music_queues[guild_id].clear()
        vc = self.ctx.voice_client
        if vc:
            await vc.disconnect()
        await update_bot_presence(None)
        await interaction.response.send_message("Kolejka wyczyszczona. Rozłączono bota.", ephemeral=True)

async def play_next(ctx):
    """Odpowiada za bezpieczne odtworzenie kolejnego utworu"""
    guild_id = ctx.guild.id
    vc = ctx.voice_client

    if not vc or not vc.is_connected():
        return

    if guild_id in music_queues and music_queues[guild_id]:
        next_track = music_queues[guild_id].pop(0)
        
        # Bezpieczne wywołanie pętli zdarzeń po zakończeniu utworu
        def after_playing(error):
            if error:
                print(f"[BŁĄD] Wyjątek podczas odtwarzania: {error}")
            coro = play_next(ctx)
            asyncio.run_coroutine_threadsafe(coro, bot.loop)

        vc.play(
            discord.FFmpegPCMAudio(next_track['url'], **FFMPEG_OPTIONS), 
            after=after_playing
        )
        await update_bot_presence(next_track['title'])
        
        embed = create_music_embed(next_track, status="Teraz odtwarzane")
        view = InteractiveControlView(ctx)
        await ctx.send(embed=embed, view=view)
    else:
        await update_bot_presence(None)
        print(f"[KANAŁ] Kolejka została zakończona dla serwera {guild_id}")

@bot.command()
async def play(ctx, *, search: str):
    """Wyszukuje i odtwarza muzykę bezpośrednio ze SoundCloud"""
    if not ctx.author.voice:
        await ctx.send("`[BŁĄD]` Musisz znajdować się na kanale głosowym, aby użyć tej komendy.")
        return

    # Kategoryczna blokada YouTube na hostingu Render z powodu banów IP
    if "youtube.com" in search or "youtu.be" in search:
        await ctx.send("`[SYSTEM]` Odtwarzanie z YouTube zostało zablokowane z przyczyn stabilności hostingu. Użyj SoundCloud.")
        return

    voice_channel = ctx.author.voice.channel
    vc = ctx.voice_client if ctx.voice_client else await voice_channel.connect()

    guild_id = ctx.guild.id
    if guild_id not in music_queues:
        music_queues[guild_id] = []

    status_msg = await ctx.send("`[SYSTEM]` Trwa pobieranie metadanych i analizowanie strumienia...")

    try:
        # Konfigurujemy jawne zapytanie wyszukiwania dla SoundCloud
        search_query = search
        if not search.startswith("http://") and not search.startswith("https://"):
            search_query = f"scsearch:{search}"

        loop = asyncio.get_event_loop()
        # Wyciągamy dane asynchronicznie, aby nie blokować głównego wątku bota
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search_query, download=False))
        
        if 'entries' in data and data['entries']:
            data = data['entries'][0]
            
        if not data or 'url' not in data:
            await status_msg.edit(content="`[BŁĄD]` Nie udało się załadować utworu. Spróbuj zmodyfikować zapytanie.")
            return

        track_info = {
            'url': data['url'],
            'original_url': data.get('webpage_url', 'https://soundcloud.com'),
            'title': data.get('title', 'Nieznany utwór'),
            'uploader': data.get('uploader', 'Nieznany artysta'),
            'duration': data.get('duration', 0),
            'thumbnail': data.get('thumbnail', None),
            'extractor': data.get('extractor_key', 'SoundCloud')
        }

        if vc.is_playing() or vc.is_paused():
            music_queues[guild_id].append(track_info)
            embed = create_music_embed(track_info, status="Dodano do kolejki")
            await status_msg.delete()
            await ctx.send(embed=embed)
        else:
            music_queues[guild_id].append(track_info)
            await status_msg.delete()
            await play_next(ctx)
            
    except Exception as e:
        print(f"[WYJĄTEK BLOKADY] Szczegóły błędu ekstrakcji: {e}")
        await status_msg.edit(content="`[BŁĄD KRYTYCZNY]` Przekroczono limit czasu połączenia. Spróbuj podać inną nazwę piosenki.")

@bot.command()
async def skip(ctx):
    """Komenda tekstowa pomijająca obecny utwór"""
    vc = ctx.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
        await ctx.send("`[SYSTEM]` Utwór został pominięty pomyślnie.")
    else:
        await ctx.send("`[BŁĄD]` Żaden utwór nie jest aktualnie odtwarzany.")

@bot.command()
async def stop(ctx):
    """Zatrzymuje muzykę, czyści kolejkę i rozłącza bota"""
    guild_id = ctx.guild.id
    if guild_id in music_queues:
        music_queues[guild_id].clear()
    vc = ctx.voice_client
    if vc:
        await vc.disconnect()
    await update_bot_presence(None)
    await ctx.send("`[SYSTEM]` Odtwarzacz zatrzymany. Kolejka została wyczyszczona.")

# --- AUTOMATYCZNE ROZŁĄCZANIE GDY KANAŁ JEST PUSTY ---
@bot.event
async def on_voice_state_update(member, before, after):
    if member.guild.voice_client:
        bot_vc = member.guild.voice_client.channel
        # Jeśli na kanale głosowym pozostanie wyłącznie bot
        if len(bot_vc.members) == 1:
            await member.guild.voice_client.disconnect()
            guild_id = member.guild.id
            if guild_id in music_queues:
                music_queues[guild_id].clear()
            await update_bot_presence(None)
            print(f"[SYSTEM] Rozłączono z kanału na serwerze {guild_id} z powodu braku słuchaczy.")

# --- SYNCHRONIZACJA KROPKI STATUSU ---
@bot.event
async def on_presence_update(before, after):
    global current_user_status
    if after.id == USER_TO_COPY_ID:
        current_user_status = after.status
        
        vc = None
        for guild in bot.guilds:
            if guild.voice_client:
                vc = guild.voice_client
                break
                
        if vc and vc.is_playing() and bot.activity:
            await bot.change_presence(status=current_user_status, activity=bot.activity)
        else:
            await bot.change_presence(status=current_user_status, activity=None)

@bot.event
async def on_ready():
    global current_user_status
    for guild in bot.guilds:
        member = guild.get_member(USER_TO_COPY_ID)
        if member:
            current_user_status = member.status
            await bot.change_presence(status=current_user_status)
            break
    print(f"[SYSTEM] Zaawansowany silnik odtwarzacza 1v98 uruchomiony prawidłowo.")

# Inicjalizacja serwera Flask i uruchomienie bota
keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))

```
            
