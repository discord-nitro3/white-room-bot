from threading import Thread
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "System integralny 1v98: Aktywny"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
    
import os
import random
import re
import base64
import string
import asyncio
import discord
from discord.ext import commands, tasks

# --- KONFIGURACJA STRUKTURALNA ---
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True  
intents.members = True    

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

TARGET_ID = 1143856525648076812  
STATUS_TAG = "[1v98]"           
AUTO_CHANNEL_ID = 1505489892174467155  # Kanał dedykowany dla automatycznych impulsów

# --- BAZA DANYCH ALFABETÓW I LINII OBRONY ---
HOMOGLIFY = {
    'A': ['А'], 'B': ['В'], 'E': ['Е'], 'H': ['Н'], 'K': ['К'],
    'M': ['М', 'Μ'], 'O': ['О', 'Ο'], 'P': ['Р', 'Ρ'], 'T': ['Т', 'Τ'],
    'X': ['Х', 'Χ'], 'Y': ['Ү'], 'a': ['а'], 'c': ['с'], 'e': ['е'],
    'i': ['і'], 'j': ['ј'], 'o': ['о'], 'p': ['р'], 'x': ['х'], 'y': ['у'],
    '0': ['𝟢', '𝟬', '𝟶', 'ʘ'], '1': ['𝟣', '𝟭', '𝟷', 'ߊ'], '2': ['𝟤', '𝟮', '𝟸', 'ϩ'],
    '3': ['𝟥', '𝟯', '𝟹', 'З', 'Ӡ'], '4': ['𝟦', '𝟰', '𝟺', 'ㄐ'], '5': ['𝟧', '𝟱', '𝟻', 'Ƽ'],
    '6': ['𝟨', '𝟲', '𝟼', 'б'], '7': ['𝟩', '𝟳', '𝟽', '𐒠'], '8': ['𝟪', '𝟴', '𝟾', '𝜽'],
    '9': ['𝟫', '𝟵', '𝟿', '୨']
}

EMOCJE_I_RIPOSTY = {
    "ZAGROŻENIE / AGRESJA": {
        "blad": "Przekroczenie barier logiki na rzecz prymitywnej ekspresji emocjonalnej. Próba zdominowania dyskusji krzykiem.",
        "riposty": [
            "Twoja agresja rośnie proporcjonalnie do braku argumentów. To fascynujące, jak szybko tracisz kontrolę.",
            "Podnoszenie głosu nie sprawi, że twoje zdanie zyska na wartości. Spróbuj jeszcze raz, tym razem spokojnie.",
            "Agresywne komunikaty są jedynie tarczą dla twojej bezradności w tej dyskusji."
        ]
    },
    "DUMA / EGO": {
        "blad": "Przecenianie własnej pozycji w strukturze. Budowanie narracji na iluzji wyższości.",
        "riposty": [
            "Projektujesz pewność siebie, której fundamenty son niezwykle kruche. Naprawdę wierzysz w to, co piszesz?",
            "Przekonanie o własnej nieomylności to najprostsza droga do popełnienia błędu. Właśnie na niego czekam.",
            "Twoje ego próbuje nadrobić braki w faktach. To dość przejrzysta strategia."
        ]
    },
    "CHAOS / DEZORIENTACJA": {
        "blad": "Brak spójnej linii obrony. Chaotyczne przeskakiwanie między wątkami z powodu paniki informacyjnej.",
        "riposty": [
            "Gubisz się we własnej narracji. Uporządkuj myśli, zanim spróbujesz sformułować kolejny wniosek.",
            "Twoja argumentacja przypomina próbę złapania pionu na ruchomych piaskach. Zero konkretów.",
            "Mówisz dużo, ale nie przekazujesz żadnej treści. Deficyt logiki próbujesz nadrobić masą słowną."
        ]
    }
}

CECHY_ANALIZY = {
    "motywacja": ["Chęć dominacji w grupie", "Ukryty kompleks niższości", "Potrzeba ciągłej walidacji", "Strach przed marginalizacją"],
    "słabość": ["Podatność na prowokacje", "Zależność od opinii innych", "Brak odporności na chłodną krytykę", "Chaos pod presją czasu"],
    "rekomendacja": ["Zastosować chłodny dystans", "Izolować w dyskusji poprzez fakty", "Ignorować zaczepki do momentu błędu"]
}

# --- FUNKCJE POMOCNICZE ---
def generate_fake_extension():
    chars = string.ascii_letters + string.digits + "-_"
    part2 = "".join(random.choice(chars) for _ in range(6))
    part3 = "".join(random.choice(chars) for _ in range(38))
    return f"{part2}.{part3}"

def parse_target_presence(member):
    current_status = member.status
    if current_status == discord.Status.offline:
        return discord.Status.offline, None

    new_activity = None
    if member.activities:
        custom_act = discord.utils.find(lambda a: a.type == discord.ActivityType.custom, member.activities)
        spotify_act = discord.utils.find(lambda a: isinstance(a, discord.Spotify), member.activities)
        generic_act = None
        for act in member.activities:
            if act.type != discord.ActivityType.custom:
                generic_act = act
                break

        if custom_act and custom_act.name:
            new_activity = discord.CustomActivity(name=f"{STATUS_TAG} {custom_act.name}")
        elif spotify_act:
            new_activity = discord.Activity(
                type=discord.ActivityType.listening,
                name=f"{STATUS_TAG} {spotify_act.title} - {spotify_act.artist}"
            )
        elif generic_act:
            if generic_act.type == discord.ActivityType.listening:
                details = getattr(generic_act, 'details', None)
                state = getattr(generic_act, 'state', None)
                full_display_name = f"{STATUS_TAG} {details} - {state}" if details and state else f"{STATUS_TAG} {generic_act.name}"
            else:
                full_display_name = f"{STATUS_TAG} {generic_act.name}"

            new_activity = discord.Activity(
                type=generic_act.type,
                name=full_display_name,
                url=getattr(generic_act, 'url', None)
            )
    return current_status, new_activity

async def send_help_panel(ctx):
    embed = discord.Embed(
        title="🎛️ 1v98 // PANEL SPECYFIKACJI OPERACYJNEJ", 
        description="Wszystkie moduły zoptymalizowane pod kątem dyskrecji i kontroli informacji.",
        color=0x1a1a1a
    )
    embed.add_field(
        name="🛠️ PROTOKOŁY PROWADZENIA DZIAŁAŃ",
        value=(
            "**`!ping`**\n└ Sprawdza stabilność połączenia z bramą API Discorda.\n\n"
            "**`!sabotaz [tryb] <tekst>`**\n└ Maskowanie ciągu znaków (`--glitch`, `--ukryty`, standard).\n\n"
            "**`!kontra <tekst_celu>`**\n└ Analizuje stan przeciwnika, udaje pisanie i generuje ripostę.\n\n"
            "**`!analiza [ID]`**\n└ Wyciąga głęboki profil psychometryczny i słabości obiektu.\n\n"
            "**`!scenariusz <@wzmianka>`**\n└ Generuje plan taktyczny rozegrania celu na podstawie teorii gier.\n\n"
            "**`!skan`**\n└ Izolacja struktur sformatowanych kursywą z czatu.\n\n"
            "**`!czystka <ilość>`**\n└ Usuwa ślady wiadomości bota/komend + autodestrukcja.\n\n"
            "**`!profil [ID]`**\n└ Ekstrakcja metadanych konta, Nitro, HEX i linków CDN.\n\n"
            "**`!avatar [ID]`**\n└ Ściąga bezpośrednie, duże linki CDN awatara/GIFu.\n\n"
            "**`!token <ID/Klucz>`**\n└ Analiza, konwersja i symulacja struktur tokenu Snowflake."
        ),
        inline=False
    )
    try:
        await ctx.message.add_reaction("✅")
        await ctx.author.send(embed=embed)
    except discord.Forbidden:
        try: await ctx.send("❌ *Transmisja zablokowana. Otwórz wiadomości prywatne (DM).*")
        except Exception: pass

# --- PĘTLA AUTOMATYCZNEGO IMPULSU (CO 30 SEKUND) ---
@tasks.loop(seconds=30)
async def takt_systemowy():
    kanal = bot.get_channel(AUTO_CHANNEL_ID)
    if kanal:
        latencja = round(bot.latency * 1000)
        embed = discord.Embed(title="⏱️ 1v98 // CYKLICZNY IMPULS SYNCHRONIZACYJNY", color=0x1a1a1a)
        embed.add_field(name="Stan procesora:", value="`STABILNY`", inline=True)
        embed.add_field(name="Opóźnienie węzła (Gateway):", value=f"`{latencja}ms`", inline=True)
        embed.set_footer(text="Automatyczna weryfikacja integralności sieci. Interwał: 30s.")
        try:
            wiadomosc = await kanal.send(embed=embed)
            await wiadomosc.add_reaction("👁️")
        except Exception:
            pass

# --- WYDARZENIA ---
@bot.event
async def on_ready():
    print(f'=== INTEGRALNY SYSTEM WHITE ROOM AKTYWNY ===')
    synced = False
    for guild in bot.guilds:
        member = guild.get_member(TARGET_ID)
        if member:
            current_status, new_activity = parse_target_presence(member)
            await bot.change_presence(status=current_status, activity=new_activity)
            synced = True
            break
    if not synced:
        await bot.change_presence(activity=discord.Game(name="White Room Simulation"), status=discord.Status.online)
    
    # Uruchomienie automatycznego cyklu pingowania po zalogowaniu bota
    if not takt_systemowy.is_running():
        takt_systemowy.start()

@bot.event
async def on_presence_update(before, after):
    if after.id != TARGET_ID: return
    current_status, new_activity = parse_target_presence(after)
    try: await bot.change_presence(status=current_status, activity=new_activity)
    except Exception: pass

@bot.event
async def on_message(message):
    if message.author.bot: return
    if message.content.strip().lower() == "1v98" or (bot.user in message.mentions and len(message.content.split()) == 1):
        ctx = await bot.get_context(message)
        await send_help_panel(ctx)
        return
    await bot.process_commands(message)

# ==================== MODUŁY WYKONAWCZE ====================

@bot.command(name='ping')
async def ping(ctx):
    latencja = round(bot.latency * 1000)
    embed = discord.Embed(title="⏱️ 1v98 // DIAGNOSTYKA SYGNAŁU BRAMY", color=0x1a1a1a)
    embed.add_field(name="Latencja magistrali API:", value=f"`{latencja}ms`", inline=False)
    embed.add_field(name="Status transmisji:", value="`POŁĄCZENIE OPTYMALNE`" if latencja < 200 else "`ZAKŁÓCENIA STRUKTURALNE`", inline=False)
    embed.set_footer(text="Kalkulacja czasu powrotu pakietu danych zakończona.")
    wiadomosc = await ctx.send(embed=embed)
    await wiadomosc.add_reaction("⚙️")

@bot.command(name='kontra')
async def kontra(ctx, *, tekst_celu: str = None):
    if tekst_celu is None: return
    async with ctx.typing():
        await asyncio.sleep(2.5)
        tekst_lower = tekst_celu.lower()
        if any(w in tekst_lower for w in ["kurw", "chuj", "zamknij", "jeb", "debil", "idiot", "?!", "!!!"]):
            kategoria = "ZAGROŻENIE / AGRESJA"
        elif any(w in tekst_lower for w in ["ja", "najlepszy", "wiem", "umiesz", "gówno", "lepsz", "beka"]):
            kategoria = "DUMA / EGO"
        else:
            kategoria = "CHAOS / DEZORIENTACJA"
        dane = EMOCJE_I_RIPOSTY[kategoria]
        wybrana_riposta = random.choice(dane["riposty"])

    embed = discord.Embed(title="🛡️ 1v98 // SYSTEM DESTRUKCJI ARGUMENTACJI", color=0x1a1a1a)
    embed.add_field(name="Przejęta treść wejściowa:", value=f"*{tekst_celu}*", inline=False)
    embed.add_field(name="Zidentyfikowany stan obiektu:", value=f"`{kategoria}`", inline=True)
    embed.add_field(name="Wykryty błąd struktury:", value=dane["blad"], inline=False)
    embed.add_field(name="Sugerowana linia kontrataku:", value=f"**{wybrana_riposta}**", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='sabotaz')
async def sabotaz(ctx, tryb: str = None, *, tekst: str = None):
    if tryb and not tryb.startswith("--"):
        tekst = f"{tryb} {tekst}" if tekst else tryb
        tryb = "--standard"
    if tekst is None: return

    wynik = []
    podmiany = 0
    zalgo_chars = ['́', '̀', '̈', '̶', '̷', '̵', '̲', '̳', '̾', '͆']

    if tryb == "--glitch":
        for l in tekst:
            wynik.append(l)
            if l != " ":
                wynik.append("".join(random.choice(zalgo_chars) for _ in range(3)))
                podmiany += 1
        znieksztalcony_tekst = "".join(wynik)
        opis_statusu = "Destrukcja struktury tekstu (Zalgo Glitch)."
    elif tryb == "--ukryty":
        znieksztalcony_tekst = "\u200b".join(list(tekst))
        podmiany = len(tekst) - 1
        opis_statusu = "Wstrzyknięto niewidoczne separatory [Zero-Width Space]."
    else:
        for l in tekst:
            if l in HOMOGLIFY:
                wynik.append(random.choice(HOMOGLIFY[l]))
                podmiany += 1
            else: wynik.append(l)
        znieksztalcony_tekst = "".join(wynik)
        opis_statusu = f"Podmieniono {podmiany} znaków na homoglify."

    embed = discord.Embed(title="⚠️ 1v98 // GENERATOR BŁĘDÓW SYSTEMOWYCH", color=0x1a1a1a)
    embed.add_field(name="Oryginalny ciąg:", value=tekst, inline=False)
    embed.add_field(name="Wygenerowany sabotaż (Skopiuj):", value=znieksztalcony_tekst, inline=False)
    embed.add_field(name="Status:", value=opis_statusu, inline=False)
    await ctx.send(embed=embed)

@bot.command(name='analiza')
async def analiza(ctx, user_id: str = None):
    if user_id is None: user_id = str(ctx.author.id)
    else: user_id = user_id.replace("<@", "").replace(">", "").replace("!", "").replace("&", "")
    try: user = await bot.fetch_user(int(user_id))
    except Exception:
        await ctx.send("❌ *Brak obiektu w zasięgu radaru.*")
        return

    random.seed(user.id)
    intel = random.randint(85, 99)
    adapt = random.randint(70, 98)
    stab = random.randint(40, 95)
    manip = random.randint(75, 99)
    motyw = random.choice(CECHY_ANALIZY["motywacja"])
    slabosc = random.choice(CECHY_ANALIZY["słabość"])
    rekomendacja = random.choice(CECHY_ANALIZY["rekomendacja"])
    random.seed()

    ocena_globalna = "KLASA A (Zasób strategiczny)" if (intel + manip) > 175 else "KLASA B (Obiekt podatny)"

    embed = discord.Embed(title=f"🧠 WHITE ROOM // KARTA EWALUACYJNA: {user.name.upper()}", color=0x1a1a1a)
    embed.add_field(name="Identyfikator obiektu", value=f"• **ID:** `{user.id}`\n• **Wiek struktury:** `{(discord.utils.utcnow() - user.created_at).days} dni`", inline=False)
    embed.add_field(name="Wskaźniki potencjału", value=f"• Inteligencja analityczna: `[ {intel}% ]`\n• Zdolności adaptacyjne: `[ {adapt}% ]`\n• Stabilność psychiczna: `[ {stab}% ]`\n• Podatność na sterowanie: `[ {100 - manip}% ]`", inline=False)
    embed.add_field(name="Profilowanie behawioralne", value=f"• **Motywacja:** {motyw}\n• **Słabość:** {slabosc}\n• **Strategia:** *{rekomendacja}*", inline=False)
    embed.add_field(name="Rekomendacja operacyjna", value=f"**{ocena_globalna}**", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='scenariusz')
async def scenariusz(ctx, user: discord.Member = None, intencja: str = "izolacja"):
    if user is None: return
    embed = discord.Embed(title=f"📈 GENERATOR SCENARIUSZY TEORII GIER // CEL: {user.name}", color=0x1a1a1a)
    embed.add_field(name="Wektor operacyjny:", value=f"`{intencja.upper()}`", inline=False)
    embed.add_field(name="Krok 1: Faza Obserwacji", value=f"Ignorowanie bezpośrednich prób kontaktu ze strony {user.name}. Cel musi poczuć brak kontroli, co wywoła u niego frustrację.", inline=False)
    embed.add_field(name="Krok 2: Punkt Zwrotny", value="Wykorzystaj komendę `!kontra` publicznie w momencie, gdy cel wykaże największe emocje. To obnaży jego niestabilność.", inline=False)
    embed.add_field(name="Krok 3: Konsolidacja", value="Przejęcie pełnej kontroli nad dyskusją poprzez natychmiastową zmianę tematu na skrajnie merytoryczny.", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='skan')
async def skan(ctx):
    await ctx.send("👁️ **[1v98 // REKONESANS]:** Rozpoczęto nasłuch...")
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        znalezione = re.findall(r'(?<!\*)\*(?!\*)([^*_]+)(?<!\*)\*(?!\*)|(?<!_)_(?!_)([^*_]+)(?<!_)_(?!_)', msg.content)
        wyniki = [match[0] if match[0] else match[1] for match in znalezione]
        embed = discord.Embed(title="🕵️ 1v98 // WYNIK SKANOWANIA", color=0x1a1a1a)
        embed.add_field(name="Wyizolowane frazy (kursywa):", value="\n".join([f"• *{s.strip()}*" for s in wyniki if s.strip()]) if wyniki else "Brak pasujących struktur.")
        await ctx.send(embed=embed)
    except discord.TimeoutError: pass

@bot.command(name='profil')
async def profil(ctx, user_id: str = None):
    if user_id is None: user_id = str(ctx.author.id)
    else: user_id = user_id.replace("<@", "").replace(">", "").replace("!", "").replace("&", "")
    try:
        user = await bot.fetch_user(int(user_id))
        raw_user = await bot.http.get_user(int(user_id))
    except Exception:
        await ctx.send("❌ *Identyfikacja niemożliwa.*")
        return

    accent_color = raw_user.get('accent_color')
    banner_hash = raw_user.get('banner')
    avatar_hash = raw_user.get('avatar')
    color_hex = f"#{accent_color:06X}" if accent_color is not None else "Brak"
    has_nitro = "Wykryto" if (avatar_hash and avatar_hash.startswith("a_")) or banner_hash else "Nie wykryto"
    
    avatar_url = f"[Link](https://cdn.discordapp.com/avatars/{user.id}/{avatar_hash}.png?size=1024)" if avatar_hash else "Brak"
    banner_url = f"[Link](https://cdn.discordapp.com/banners/{user.id}/{banner_hash}.png?size=1024)" if banner_hash else "Brak"
    konto_dni = (discord.utils.utcnow() - user.created_at).days

    embed = discord.Embed(title=f"🛑 1v98 // PORTRET METADANYCH: {user.name.upper()}", color=0x1a1a1a)
    embed.add_field(name="Identyfikacja", value=f"• **Nazwa:** `{user.name}`\n• **ID:** `{user.id}`", inline=False)
    embed.add_field(name="Zasoby", value=f"• **Awatar:** {avatar_url}\n• **Baner:** {banner_url}\n• **Premium:** `{has_nitro}`\n• **HEX:** `{color_hex}`", inline=False)
    embed.add_field(name="Oś czasu", value=f"• **Rejestracja:** {user.created_at.strftime('%Y-%m-%d')}\n• **Wiek:** `{konto_dni} dni`", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='avatar')
async def avatar(ctx, user_id: str = None):
    if user_id is None: user_id = str(ctx.author.id)
    else: user_id = user_id.replace("<@", "").replace(">", "").replace("!", "").replace("&", "")
    try:
        user = await bot.fetch_user(int(user_id))
        raw_user = await bot.http.get_user(int(user_id))
    except Exception: return
    avatar_hash = raw_user.get('avatar')
    embed = discord.Embed(title=f"🖼️ REKUPERACJA: {user.name.upper()}", color=0x1a1a1a)
    if avatar_hash:
        ext = "gif" if avatar_hash.startswith("a_") else "png"
        url = f"https://cdn.discordapp.com/avatars/{user.id}/{avatar_hash}.{ext}?size=1024"
        embed.set_image(url=url)
        embed.add_field(name="Zasób CDN", value=f"[Link bezpośredni do pliku]({url})")
    else: embed.add_field(name="Modyfikacja", value="Brak niestandardowej grafiki.")
    await ctx.send(embed=embed)

@bot.command(name='token')
async def token(ctx, wejscie: str = None):
    if wejscie is None: czyste = str(ctx.author.id)
    else: czyste = wejscie.replace("<@", "").replace(">", "").replace("!", "").replace("&", "")
    embed = discord.Embed(title="🕵️ 1v98 // DEKODER KLUCZY TOKEN", color=0x1a1a1a)
    if czyste.isdigit():
        try:
            user = await bot.fetch_user(int(czyste))
            encoded_id = base64.b64encode(czyste.encode('utf-8')).decode('utf-8').rstrip("=")
            wynik = f"• **Zdekodowane ID:** `{user.id}`\n• **Obiekt:** `{user.name}`\n• **Generowany ciąg:**\n`{encoded_id}.{generate_fake_extension()}`"
        except Exception: wynik = "• **API Status:** Brak obiektu."
    else:
        fragment = wejscie.split('.')[0] if wejscie else ""
        try:
            missing_padding = len(fragment) % 4
            if missing_padding: fragment += '=' * (4 - missing_padding)
            decoded_id = base64.b64decode(fragment).decode('utf-8')
            if decoded_id.isdigit():
                user = await bot.fetch_user(int(decoded_id))
                wynik = f"• **Zdekodowane ID:** `{user.id}`\n• **Obiekt:** `{user.name}`\n• **Utworzenie:** {user.created_at.strftime('%Y-%m-%d')}"
            else: wynik = "• **Błąd:** Wadliwy Snowflake."
        except Exception: wynik = "• **Błąd:** Naruszona struktura Base64."
    embed.add_field(name="Analiza algorytmiczna:", value=wynik, inline=False)
    await ctx.send(embed=embed)

@bot.command(name='czystka')
@commands.has_permissions(manage_messages=True)
async def czystka(ctx, ilosc: int = 5):
    try: await ctx.message.delete()
    except discord.Forbidden: pass
    def jest_botem_lub_komenda(m): return m.author == bot.user or m.content.startswith('!')
    deleted = await ctx.channel.purge(limit=ilosc, check=jest_botem_lub_komenda)
    potwierdzenie = await ctx.send(f"🧹 *Usunięto {len(deleted)} śladów systemowych ze strumienia danych.*")
    await asyncio.sleep(3)
    await potwierdzenie.delete()

@czystka.error
async def czystka_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Protokół czyszczenia zablokowany. Brak uprawnień administracyjnych.", delete_after=5)
keep_alive()
# --- URUCHOMIENIE ---
try:
    bot.run(os.environ['DISCORD_TOKEN'])
except Exception as e:
    print(f"Krytyczny błąd API: {e}")
