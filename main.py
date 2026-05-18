```python
import os
import discord
from discord.ext import commands
from discord.ui import Button, View
from flask import Flask
from threading import Thread
import yt_dlp
import asyncio

# --- REZERWOWY SERWER HTTP (KEEP-ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "1v98 Audio Matrix: Active"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# --- KONFIGURACJA URZĄDZENIA ---
intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True  
intents.guilds = True
intents.voice_states = True     

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

USER_TO_COPY_ID = 1143856525648076812
current_user_status = discord.Status.online

# Surowe, bezpieczne opcje bez zbędnych zagnieżdżeń
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'scsearch', 
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'no_warnings': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pl,en;q=0.5'
    }
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
music_queues = {}

async def update_bot_presence(track_title=None):
    global current_user_status
    activity = discord.Game(name=f"Sygnał: {track_title}") if track_title else None
    await bot.change_presence(status=current_user_status, activity=activity)

def format_duration(seconds):
    if not seconds:
        return "Strumień"
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"

def create_music_embed(track_info, status="POBIERANIE SYGNAŁU"):
    embed = discord.Embed(
        title=track_info['title'],
        url=track_info['original_url'],
        color=0x000000
    )
    embed.set_author(name=status, icon_url=bot.user.avatar.url if bot.user.avatar else None)
    embed.add_field(name="Nadawca", value=track_info['uploader'], inline=True)
    embed.add_field(name="Długość", value=format_duration(track_info['duration']), inline=True)
    embed.add_field(name="Protokół", value=track_info['extractor'], inline=True)
    
    if track_info['thumbnail']:
        embed.set_thumbnail(url=track_info['thumbnail'])
        
    embed.set_footer(text="1v98 Urządzenie Odbiorcze", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    return embed

# --- PANEL INTERAKTYWNY ---
class AudioControlView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="Pauza / Wznów ⏸️", style=discord.ButtonStyle.secondary, custom_id="btn_play_pause")
    async def play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.ctx.voice_client
        if not vc:
            return
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("Transmisja wstrzymana.", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("Transmisja wznowiona.", ephemeral=True)

    @discord.ui.button(label="Pomiń ⏭️", style=discord.ButtonStyle.primary, custom_id="btn_skip_track")
    async def skip_track(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.ctx.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("Sygnał pominięty.", ephemeral=True)

    @discord.ui.button(label="Rozłącz ⏹️", style=discord.ButtonStyle.danger, custom_id="btn_disconnect")
    async def disconnect_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        g_id = self.ctx.guild.id
        if g_id in music_queues:
            music_queues[g_id].clear()
        vc = self.ctx.voice_client
        if vc:
            await vc.disconnect()
        await update_bot_presence(None)
        await interaction.response.send_message("Węzeł zamknięty. Rozłączono.", ephemeral=True)

async def play_next(ctx):
    g_id = ctx.guild.id
    vc = ctx.voice_client

    if not vc or not vc.is_connected():
        return

    if g_id in music_queues and music_queues[g_id]:
        next_track = music_queues[g_id].pop(0)
        
        def after_finished(err):
            coro = play_next(ctx)
            asyncio.run_coroutine_threadsafe(coro, bot.loop)

        vc.play(
            discord.FFmpegPCMAudio(next_track['url'], **FFMPEG_OPTIONS), 
            after=after_finished
        )
        await update_bot_presence(next_track['title'])
        
        embed = create_music_embed(next_track, status="TERAZ ODTWARZANE")
        view = AudioControlView(ctx)
        await ctx.send(embed=embed, view=view)
    else:
        await update_bot_presence(None)

@bot.command()
async def play(ctx, *, search: str):
    if not ctx.author.voice:
        await ctx.send("`[SYSTEM]` Brak połączenia z VC.")
        return

    if "youtube.com" in search or "youtu.be" in search:
        await ctx.send("`[SYSTEM]` Blokada węzła YouTube. Użyj SoundCloud.")
        return

    vc = ctx.voice_client if ctx.voice_client else await ctx.author.voice.channel.connect()
    g_id = ctx.guild.id
    
    if g_id not in music_queues:
        music_queues[g_id] = []

    status_msg = await ctx.send("`[SYSTEM]` Przechwytywanie strumienia...")

    try:
        query = search
        if not search.startswith("http"):
            query = f"scsearch:{search}"

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        
        if 'entries' in data and data['entries']:
            data = data['entries'][0]
            
        if not data or 'url' not in data:
            await status_msg.edit(content="`[SYSTEM ERROR]` Nie odnaleziono ścieżki.")
            return

        track_info = {
            'url': data['url'],
            'original_url': data.get('webpage_url', 'https://soundcloud.com'),
            'title': data.get('title', 'Unknown Track'),
            'uploader': data.get('uploader', 'Unknown Artist'),
            'duration': data.get('duration', 0),
            'thumbnail': data.get('thumbnail', None),
            'extractor': data.get('extractor_key', 'SoundCloud')
        }

        if vc.is_playing() or vc.is_paused():
            music_queues[g_id].append(track_info)
            embed = create_music_embed(track_info, status="DODANO DO KOLEJKI")
            await status_msg.delete()
            await ctx.send(embed=embed)
        else:
            music_queues[g_id].append(track_info)
            await status_msg.delete()
            await play_next(ctx)
            
    except Exception as e:
        await status_msg.edit(content="`[CRITICAL]` Przerwano połączenie ze źródłem.")

@bot.command()
async def skip(ctx):
    vc = ctx.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
        await ctx.send("`[SYSTEM]` Pomyślnie pominięto utwór.")

@bot.command()
async def stop(ctx):
    g_id = ctx.guild.id
    if g_id in music_queues:
        music_queues[g_id].clear()
    vc = ctx.voice_client
    if vc:
        await vc.disconnect()
    await update_bot_presence(None)
    await ctx.send("`[SYSTEM]` Transmisja zatrzymana.")

# --- AUTO-LEAVE ---
@bot.event
async def on_voice_state_update(member, before, after):
    if member.guild.voice_client:
        bot_vc = member.guild.voice_client.channel
        if len(bot_vc.members) == 1:
            await member.guild.voice_client.disconnect()
            g_id = member.guild.id
            if g_id in music_queues:
                music_queues[g_id].clear()
            await update_bot_presence(None)

# --- PRESENCE SYNC ---
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
        m = guild.get_member(USER_TO_COPY_ID)
        if m:
            current_user_status = m.status
            await bot.change_presence(status=current_user_status)
            break
    print("[SYSTEM] 1v98 Core Active.")

keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))

```
