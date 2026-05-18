import os
import discord
from discord.ext import commands
from discord.ui import Button, View
from flask import Flask
from threading import Thread
import yt_dlp
import asyncio

# --- FLASK SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "1v99 Ultimate Engine: Active"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# --- REPLIKATOR & AUDIO PRO CORPS (1v99) ---
intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True  
intents.guilds = True
intents.voice_states = True     

# Dodanie obsługi pingu jako alternatywnego prefixu bota
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), intents=intents, help_command=None)

USER_TO_COPY_ID = 1143856525648076812

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'scsearch', 
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'no_warnings': True,
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
music_queues = {}
current_user_status = discord.Status.online

async def update_bot_presence(track_title=None):
    global current_user_status
    activity = discord.Game(name=f"Playing: {track_title}") if track_title else None
    await bot.change_presence(status=current_user_status, activity=activity)

def format_duration(seconds):
    if not seconds:
        return "Live Stream"
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def create_music_embed(track_info, status="Now Playing"):
    embed = discord.Embed(
        title=track_info['title'],
        url=track_info['original_url'],
        color=0x000000
    )
    embed.set_author(name=status, icon_url=bot.user.avatar.url if bot.user.avatar else None)
    embed.add_field(name="Uploader", value=track_info['uploader'], inline=True)
    embed.add_field(name="Duration", value=format_duration(track_info['duration']), inline=True)
    embed.add_field(name="Source", value=track_info['extractor'], inline=True)
    
    if track_info['thumbnail']:
        embed.set_thumbnail(url=track_info['thumbnail'])
        
    embed.set_footer(text="1v99 Core Integration", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    return embed

# --- MUSIC PANEL BUTTONS ---
class MusicControlView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="Skip ⏭️", style=discord.ButtonStyle.secondary, custom_id="btn_skip")
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.ctx.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("Track skipped via control interface.", ephemeral=True)
        else:
            await interaction.response.send_message("No active playback found.", ephemeral=True)

    @discord.ui.button(label="Stop & Clear ⏹️", style=discord.ButtonStyle.danger, custom_id="btn_clear")
    async def clear_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.ctx.guild.id
        if guild_id in music_queues:
            music_queues[guild_id].clear()
        vc = self.ctx.voice_client
        if vc:
            await vc.disconnect()
        await update_bot_presence(None)
        await interaction.response.send_message("Queue purged. System disconnected.", ephemeral=True)

def check_queue(ctx):
    guild_id = ctx.guild.id
    vc = ctx.voice_client

    if guild_id in music_queues and music_queues[guild_id]:
        next_track = music_queues[guild_id].pop(0)
        
        vc.play(
            discord.FFmpegPCMAudio(next_track['url'], **FFMPEG_OPTIONS), 
            after=lambda e: check_queue(ctx)
        )
        bot.loop.create_task(update_bot_presence(next_track['title']))
        
        embed = create_music_embed(next_track, status="Now Playing")
        view = MusicControlView(ctx)
        bot.loop.create_task(ctx.send(embed=embed, view=view))
    else:
        bot.loop.create_task(update_bot_presence(None))
        print(f"[VOICE] Queue concluded for guild {guild_id}")

# --- COMMANDS SECTION ---
@bot.command()
async def play(ctx, *, search: str):
    if not ctx.author.voice:
        return

    if "youtube.com" in search or "youtu.be" in search:
        await ctx.send("`[ERROR]` YouTube extraction is restricted. Use SoundCloud queries.")
        return

    voice_channel = ctx.author.voice.channel
    vc = ctx.voice_client if ctx.voice_client else await voice_channel.connect()

    guild_id = ctx.guild.id
    if guild_id not in music_queues:
        music_queues[guild_id] = []

    status_msg = await ctx.send("`[SYSTEM]` Fetching track metadata...")

    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search, download=False))
        
        if 'entries' in data and data['entries']:
            data = data['entries'][0]
            
        if not data:
            await status_msg.edit(content="`[ERROR]` Target track unresolved.")
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

        if vc.is_playing():
            music_queues[guild_id].append(track_info)
            embed = create_music_embed(track_info, status="Track Enqueued")
            await status_msg.delete()
            await ctx.send(embed=embed)
        else:
            vc.play(
                discord.FFmpegPCMAudio(track_info['url'], **FFMPEG_OPTIONS), 
                after=lambda e: check_queue(ctx)
            )
            await update_bot_presence(track_info['title'])
            
            embed = create_music_embed(track_info, status="Now Playing")
            view = MusicControlView(ctx)
            await status_msg.delete()
            await ctx.send(embed=embed, view=view)
            
    except Exception as e:
        print(f"[ERROR] Stream exception: {e}")
        await status_msg.edit(content="`[CRITICAL]` Streaming subsystem failed.")

@bot.command(name="queue", aliases=["q"])
async def show_queue(ctx):
    guild_id = ctx.guild.id
    if guild_id in music_queues and music_queues[guild_id]:
        tracks = "\n".join([f"[{i+1:02d}] {track['title']} ({format_duration(track['duration'])})" for i, track in enumerate(music_queues[guild_id])])
        await ctx.send(f"```ini\n[1v99 SYSTEM PENDING QUEUE]\n{tracks}\n```")
    else:
        await ctx.send("`[SYSTEM]` Audio queue is empty.")

@bot.command()
async def skip(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await ctx.send("`[SYSTEM]` Track terminated manually.")

@bot.command()
async def clear(ctx):
    guild_id = ctx.guild.id
    if guild_id in music_queues:
        music_queues[guild_id].clear()
    vc = ctx.voice_client
    if vc:
        await vc.disconnect()
    await update_bot_presence(None)
    await ctx.send("`[SYSTEM]` Matrix reset. Voice connection unlinked.")

@bot.command()
async def status(ctx):
    member = ctx.guild.get_member(USER_TO_COPY_ID)
    user_dot = member.status if member else "unresolved"
    await ctx.send(
        f"```yaml\n"
        f"1v99 // INTEGRITY CONTROL\n"
        f"-------------------------\n"
        f"Network Latency : {round(bot.latency * 1000)}ms\n"
        f"Presence Link   : {user_dot}\n"
        f"Core State      : Operational\n"
        f"```"
    )

@bot.command(name="help", aliases=["h"])
async def pro_help(ctx):
    """Zaawansowana, szczegółowa komenda pomocy w surowym stylu"""
    embed = discord.Embed(
        title="1v99 SYSTEM COMMAND MANIFEST",
        description="All commands can be invoked using either the `!` prefix or by directly mentioning the bot (@1v99).",
        color=0x000000
    )
    embed.add_field(name="🎵 !play [query / link]", value="Streams audio via SoundCloud. Supplying text triggers search parameters.", inline=False)
    embed.add_field(name="⏭️ !skip", value="Forces termination of current track and advances queue matrix.", inline=False)
    embed.add_field(name="📋 !queue / !q", value="Exhibits all pending tracks queued for playback.", inline=False)
    embed.add_field(name="⏹️ !clear", value="Flushes queue entirely and disconnects from the voice node.", inline=False)
    embed.add_field(name="📊 !status", value="Performs a real-time system and latency diagnostic checklist.", inline=False)
    embed.add_field(name="ℹ️ !help / !h", value="Displays this mainframe instruction matrix.", inline=False)
    
    embed.set_footer(text="1v99 Core Interface Protocol")
    await ctx.send(embed=embed)

# --- AUTOMATIC LEAVE TRIGGER ---
@bot.event
async def on_voice_state_update(member, before, after):
    if member.guild.voice_client:
        bot_vc = member.guild.voice_client.channel
        if len(bot_vc.members) == 1:
            await member.guild.voice_client.disconnect()
            guild_id = member.guild.id
            if guild_id in music_queues:
                music_queues[guild_id].clear()
            await update_bot_presence(None)
            print(f"[VOICE] Auto-vacated due to lack of users.")

# --- APERIODIC MEN-TRIGGER HANDLING ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return
        
    # Jeśli bot został tylko spingowany bez dodatkowego tekstu, wypluj systemowy help panel
    if bot.user.mentioned_in(message) and len(message.content.strip().split()) == 1:
        ctx = await bot.get_context(message)
        await pro_help(ctx)
        return

    await bot.process_commands(message)

# --- PRESENCE CLONING subsystem ---
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
    print(f"[SYSTEM] 1v99 Absolute Core Deployed.")

# --- SYSTEM EXECUTION ---
keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))
