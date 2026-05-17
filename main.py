import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

# --- SUROWY SERWER FLASK ---
app = Flask('')

@app.route('/')
def home():
    return "MP3 Voice Sync: Active"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# --- REPLIKATOR & MP3 AUDIO (1v99) ---
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

@bot.command()
async def play(ctx):
    # 1. Sprawdzenie czy użytkownik jest na VC
    if not ctx.author.voice:
        return

    # 2. Sprawdzenie czy do wiadomości dodano załącznik
    if not ctx.message.attachments:
        await ctx.send("playing nothing // BRAK PLIKU MP3 W ZAŁĄCZNIKU")
        return

    attachment = ctx.message.attachments[0]
    
    # Akceptujemy tylko pliki audio (mp3, wav, m4a itp.)
    if not attachment.content_type or not attachment.content_type.startswith('audio/'):
        await ctx.send("playing nothing // ZAŁĄCZNIK NIE JEST PLIKIEM AUDIO")
        return

    voice_channel = ctx.author.voice.channel
    
    # Łączenie z VC
    if ctx.voice_client is None:
        vc = await voice_channel.connect()
    else:
        vc = ctx.voice_client

    try:
        if vc.is_playing():
            vc.stop()
            
        # Odtwarzanie bezpośredniego linku do pliku z serwerów Discorda (błyskawiczne i bezbłędne)
        vc.play(discord.FFmpegPCMAudio(attachment.url, **FFMPEG_OPTIONS))
        
        # Chłodny meldunek na kanale tekstowym
        await ctx.send(f"playing {attachment.filename}")
        print(f"[VOICE] Odtwarzanie pliku: {attachment.filename}")
        
    except Exception as e:
        print(f"[ERROR] Błąd odtwarzania MP3: {e}")

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
    print(f"[SYSTEM] Protokół 1v99 aktywowany. Tryb: Direct MP3 Player.")

# --- ROZRUCH ---
keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))
