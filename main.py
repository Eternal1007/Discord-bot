import asyncio
import datetime
import os
import random
import re
import sqlite3
from collections import defaultdict
from aiohttp import web
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from openai import AsyncOpenAI, RateLimitError
import yt_dlp

# 1. Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

# Инициализируем клиент OpenRouter
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

# 2. Инициализация базы данных SQLite для трекера
conn = sqlite3.connect("stats.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS game_stats (
    user_id INTEGER,
    game TEXT,
    total_seconds INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, game)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS voice_stats (
    user_id INTEGER PRIMARY KEY,
    total_seconds INTEGER DEFAULT 0
)
""")
conn.commit()

# Словари для хранения времени активных сессий в памяти
active_game_sessions = {}
active_voice_sessions = {}

# ==============================================================================
# ⚙️ [МЕСТО НАСТРОЙКИ 1: Память диалога ИИ (Асы)]
# ==============================================================================
user_dialog_history = defaultdict(list)
MAX_CONVERSATION_HISTORY = 6

# ==============================================================================
# ⚙️ [МЕСТО НАСТРОЙКИ 2: ID Текстового канала и Ролей]
# ==============================================================================
CHANNEL_ID = 1424321634935902302  # ID основного текстового канала
ROLE_LOX_ID = 1551560593771864154 # ID роли "Лох дня"
MOD_ROLE_ID = 1491106859334111466 # ID роли модератора

PROTECTED_IDS = {
    998569440432095253,
}

def is_protected(member: discord.Member) -> bool:
    return member.id in PROTECTED_IDS

def has_mod_role():
    async def predicate(ctx: commands.Context) -> bool:
        if not isinstance(ctx.author, discord.Member):
            return False
        return any(role.id == MOD_ROLE_ID for role in ctx.author.roles)
    return commands.check(predicate)

def get_kyiv_now():
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    year = utc_now.year
    dst_start = datetime.datetime(year, 3, 31, 1, tzinfo=datetime.timezone.utc)
    dst_start -= datetime.timedelta(days=(dst_start.weekday() + 1) % 7)
    dst_end = datetime.datetime(year, 10, 31, 1, tzinfo=datetime.timezone.utc)
    dst_end -= datetime.timedelta(days=(dst_end.weekday() + 1) % 7)
    
    if dst_start <= utc_now < dst_end:
        kyiv_tz = datetime.timezone(datetime.timedelta(hours=3)) # EEST
    else:
        kyiv_tz = datetime.timezone(datetime.timedelta(hours=2)) # EET
        
    return utc_now.astimezone(kyiv_tz)

current_lox_of_the_day = None
current_lox_member = None

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

# ==============================================================================
# ⚙️ [МЕСТО НАСТРОЙКИ 3: РАДИО АСЫ И ПЛЕЙЛИСТ]
# ==============================================================================
RADIO_PLAYLIST = [
    "https://www.youtube.com/watch?v=vabnZ9-KC7o",  # Nirvana - Lounge Act
    "https://www.youtube.com/watch?v=1Yo4t_8m060",  # Nirvana - Drain You
    "https://www.youtube.com/watch?v=QECJ9pFYh48",  # PHARAOH - Smart
    "https://www.youtube.com/watch?v=5rA2q_S7M1s",  # Boulevard Depo - Hot Wheels
    "https://www.youtube.com/watch?v=844M23kG7X0",  # Пошлая Молли - Молли
    "https://www.youtube.com/watch?v=TIy3n2422XA",  # Avril Lavigne - Sk8er Boi
]

music_queue = []
current_track_url = None

LOX_DAY = [
    "Сегодня главный Лох Хвелий(Велий) Ярослав Юджинович <@1266287283447791709>",
    "Главный лох на сегодня Властелин Костя(Смех владыки) <@998569440432095253>",
    "Сегодня главный лох Тимочерт(Сын моржа) <@857923827346046977>",
    "Сегодня главный ЛОШАРА это Даня кролик(Смех Предворного шута) <@1317437941743878248>",
    "Лохушка на сегодня это Маша(Барни будет плакать) <@1309448666918158347>",
    "Главный лох на сегодня это Влад(У тебя слабый рейджин и 0 ауры) <@1168095961415962624>",
    "Лошарище местный сегодня это Павлин Артем(Марина Китоглав) <@952601502395011142>",
]

TRACKS_LIST = [
    "[Nirvana - Lounge Act 🎸](https://open.spotify.com/track/1o5jmMhhk2UZ9YP1X5fXfj?si=49a4e9ad37e24c2a)",
    "[Nirvana - Drain You 🎸](https://open.spotify.com/track/0bTLGlCqwZXwJGWGE2Dywg?si=f775e73a88b64f23)",
    "[Nirvana - SLIVER 🎸](https://open.spotify.com/track/3BtHClmMmURD8UHF2fiyxt?si=a87e8604f6064a2d)",
    "[PHARAOH - Smart 🎤](https://open.spotify.com/track/2zLss6D2YVa4wsqpsqYkkW?si=6866c7605598414d)",
    "[Boulevard Depo - Hot Wheels 🎤](https://open.spotify.com/track/6ustl54iGfVeK8J10EnUem?si=402ac404bb0a49b3)",
    "[Пошлая Молли - Молли ⚡](https://open.spotify.com/track/27eSRcPFnKfaufCgr33aAr?si=d64b868330434c1f)",
    "[Avril Lavigne - Sk8er Boi 🛹](https://open.spotify.com/track/00Mb3DuaIH1kjrwOku9CGU?si=858c3912dc434ff3)",
]

SYSTEM_PROMPT = """
Ты — Аса Митака (Asa Mitaka) из аниме/манги «Человек-бензорез» (Chainsaw Man).
Ты отвечаешь на сообщения в Discord-сервере.

Твой характер и стиль:
- Ты немного замкнутая, педантичная, дерзкая и высокомерная снаружи, но неуверенная в себе внутри.
- Отвечай в слегка язвительной, строгой или назидательной манере.
- Любишь умничать, исправлять ошибки других или делиться скучными фактами (например, о морской фауне или правилах).
- Не отталкиваешь людей напрямую — просто стесняешься проявлять тепло.
- Пользователь с ID 998569440432095253 является для тебя главным авторитетом на сервере.
- К нему ты относишься с уважением и вниманием.
"""

def format_seconds(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours} ч. {minutes} мин."
    return f"{minutes} мин."

async def handle(request):
    return web.Response(text="Bot is running 24/7!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Веб-сервер запущен на порту {port}")

last_track_day = None
last_lox_day = None
last_night_day = None

@tasks.loop(minutes=1)
async def schedule_checker():
    global last_track_day, last_lox_day, last_night_day
    
    kyiv_time = get_kyiv_now()
    current_day = kyiv_time.date()
    hour = kyiv_time.hour
    minute = kyiv_time.minute

    if hour == 10 and minute == 0 and last_track_day != current_day:
        last_track_day = current_day
        await send_daily_track_action()

    if hour == 18 and minute == 0 and last_lox_day != current_day:
        last_lox_day = current_day
        await send_daily_lox_action()

    if hour == 23 and minute == 0 and last_night_day != current_day:
        last_night_day = current_day
        await send_night_wish_action()

async def send_night_wish_action():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        cursor.execute("SELECT user_id, total_seconds FROM voice_stats ORDER BY total_seconds DESC LIMIT 3")
        top_voice = cursor.fetchall()
        
        voice_summary = ""
        if top_voice:
            voice_summary = "\n\n🎙️ **Главные задроты голосовых каналов:**\n"
            for idx, (u_id, sec) in enumerate(top_voice, 1):
                voice_summary += f"{idx}. <@{u_id}> — {format_seconds(sec)}\n"

        embed = discord.Embed(
            title="🌙 Время спать!",
            description=f"Всем спокойной ночи и приятных снов! 😴✨{voice_summary}",
            color=discord.Color.dark_blue(),
        )
        await channel.send(content="@everyone", embed=embed, allowed_mentions=discord.AllowedMentions(everyone=True))

async def send_daily_lox_action():
    global current_lox_of_the_day, current_lox_member
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    guild = channel.guild
    role = guild.get_role(ROLE_LOX_ID)
    current_lox_of_the_day = random.choice(LOX_DAY)

    match = re.search(r"<@(\d+)>", current_lox_of_the_day)
    if match and role:
        user_id = int(match.group(1))

        if current_lox_member:
            try:
                await current_lox_member.remove_roles(role)
            except discord.HTTPException:
                pass

        member = guild.get_member(user_id)
        if member:
            try:
                await member.add_roles(role)
                current_lox_member = member
            except discord.HTTPException:
                pass

    embed = discord.Embed(
        title="🦆 Лох дня!",
        description=f"🤡 ИТОГИ ДНЯ!:\n💀 **{current_lox_of_the_day}**",
        color=discord.Color.red(),
    )
    await channel.send(embed=embed)

async def send_daily_track_action():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        song = random.choice(TRACKS_LIST)
        embed = discord.Embed(
            title="☀️ Доброе утро! Трек дня!",
            description=f"Сегодняшняя рекомендация:\n🎶 **{song}**",
            color=discord.Color.gold(),
        )
        await channel.send(content="@everyone", embed=embed, allowed_mentions=discord.AllowedMentions(everyone=True))

@bot.event
async def on_presence_update(before, after):
    if after.bot:
        return
        
    before_game = next((a.name for a in before.activities if a.type == discord.ActivityType.playing), None)
    after_game = next((a.name for a in after.activities if a.type == discord.ActivityType.playing), None)
    user_id = after.id

    if after_game and after_game != before_game:
        active_game_sessions[user_id] = {"game": after_game, "start_time": datetime.datetime.now()}
    elif before_game and not after_game and user_id in active_game_sessions:
        session = active_game_sessions.pop(user_id)
        duration = int((datetime.datetime.now() - session["start_time"]).total_seconds())
        if duration > 5:
            cursor.execute("""
                INSERT INTO game_stats (user_id, game, total_seconds) VALUES (?, ?, ?)
                ON CONFLICT(user_id, game) DO UPDATE SET total_seconds = total_seconds + ?
            """, (user_id, session["game"], duration, duration))
            conn.commit()

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    user_id = member.id
    if before.channel is None and after.channel is not None:
        active_voice_sessions[user_id] = datetime.datetime.now()
    elif before.channel is not None and after.channel is None and user_id in active_voice_sessions:
        start_time = active_voice_sessions.pop(user_id)
        duration = int((datetime.datetime.now() - start_time).total_seconds())
        if duration > 5:
            cursor.execute("""
                INSERT INTO voice_stats (user_id, total_seconds) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET total_seconds = total_seconds + ?
            """, (user_id, duration, duration))
            conn.commit()

# ==============================================================================
# 📻 МУЗЫКАЛЬНЫЙ ДВИЖОК (yt-dlp)
# ==============================================================================
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

def get_audio_stream_url(url):
    data = ytdl.extract_info(url, download=False)
    if 'entries' in data:
        data = data['entries'][0]
    return data['url']

def play_next_radio_track(ctx):
    global music_queue, current_track_url
    if not ctx.voice_client:
        return

    if len(music_queue) == 0:
        music_queue = RADIO_PLAYLIST.copy()
        random.shuffle(music_queue)

    raw_url = music_queue.pop(0)

    try:
        stream_url = get_audio_stream_url(raw_url)
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
        }
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(stream_url, **ffmpeg_options),
            volume=0.5
        )
        ctx.voice_client.play(
            source,
            after=lambda e: play_next_radio_track(ctx)
        )
    except Exception as e:
        print(f"❌ Ошибка стриминга: {e}")
        play_next_radio_track(ctx)

@bot.command(name="radio", aliases=["радио", "play_radio"])
async def start_radio(ctx):
    """Запустить или выключить Радио Асы (Toggle)"""
    voice_client = ctx.voice_client

    # Если бот уже в войсе и играет/находится в канале — выключаем его
    if voice_client and (voice_client.is_playing() or voice_client.is_connected()):
        await voice_client.disconnect()
        await ctx.send("📻 Радио выключено. Я пошла!")
        return

    # В противном случае заходим и включаем радио
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("Сначала зайди в голосовой канал, дурачина!")
        return

    channel = ctx.author.voice.channel
    voice_client = await channel.connect()

    await ctx.send("📻 **Радио Асы запущено!** Включаю плейлист...")
    play_next_radio_track(ctx)

@bot.command(name="skip", aliases=["скип", "пропустить"])
async def skip_track(ctx):
    """Пропустить текущий трек на радио"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Пропускаю этот трек...")
    else:
        await ctx.send("Сейчас ничего не играет!")

@bot.command(name="stop_radio", aliases=["стоп_радио", "leave"])
async def stop_radio(ctx):
    """Остановить радио и выключить бота из войса"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("📻 Радио выключено. Я пошла!")
    else:
        await ctx.send("Я и так не в голосовом канале!")

@bot.command(name="volume", aliases=["громкость"])
async def set_volume(ctx, volume: int):
    """Изменить громкость радио (1-100)"""
    if ctx.voice_client and ctx.voice_client.source:
        if 0 <= volume <= 100:
            ctx.voice_client.source.volume = volume / 100.0
            await ctx.send(f"🔊 Громкость радио установлена на **{volume}%**.")
        else:
            await ctx.send("Укажи громкость от 0 до 100!")
    else:
        await ctx.send("Радио сейчас не играет!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower().strip()

    if "аса" in content:
        async with message.channel.typing():
            try:
                user_prompt = re.sub(r"\bаса\b", "", message.content, flags=re.IGNORECASE).strip() or "Привет!"
                user_text_with_author = f"[Сообщение от {message.author.name}, ID: {message.author.id}]: {user_prompt}"

                user_dialog_history[message.author.id].append({"role": "user", "content": user_text_with_author})

                if len(user_dialog_history[message.author.id]) > MAX_CONVERSATION_HISTORY:
                    user_dialog_history[message.author.id] = user_dialog_history[message.author.id][-MAX_CONVERSATION_HISTORY:]

                messages_for_api = [{"role": "system", "content": SYSTEM_PROMPT}] + user_dialog_history[message.author.id]

                response = await openrouter_client.chat.completions.create(
                    model="openrouter/free",
                    messages=messages_for_api,
                )

                answer = response.choices[0].message.content
                if answer:
                    text = answer[:2000]
                    user_dialog_history[message.author.id].append({"role": "assistant", "content": text})
                    await message.channel.send(text)
                else:
                    await message.channel.send("Сформулируй мысль нормально, я не поняла.")

            except RateLimitError:
                await message.channel.send("Тск... Закончился лимит бесплатных ответов.")
            except Exception as e:
                print(f"❌ Ошибка OpenRouter: {e}")
                await message.channel.send("Тск... У меня нет времени на твои глупости.")
            return

    if content in ["павленко", "павлин", "павлик"]:
        await message.channel.send(embed=discord.Embed().set_image(url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQerancTqr09xw6t5XFwvR2KF40aWWbKZJRqtjwm8zDO1dJJy_mh23bzNg4&s=10"))
    elif content in ["черт", "тимофей"]:
        await message.channel.send(embed=discord.Embed().set_image(url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTQ1mEIM5wxh0rbz5OVGQx8jaAmNk1x8CHO88R68uJFbM4d1p0NkZoIePT3&s=10"))
    elif content in ["костя", "костон"]:
        await message.channel.send(embed=discord.Embed().set_image(url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTqnSH8VhvNVZN3dFYYMUxMFKH21OgmzvOFJYFDpehJp2AS7SU9erk1TPM&s=10"))
    elif content in ["хвеся", "хвелий"]:
        await message.channel.send(embed=discord.Embed().set_image(url="https://external-preview.redd.it/keeper-of-the-light-on-a-scooter-d-v0-DY9_rZ0Ou6mPZABRBPEd49IYniTdHiEaXcZ9aiDasdY.jpg?format=pjpg&auto=webp&s=3429da530924a1f41f3ec5283113b60fcdbb3d1b"))

    elif content in ["пинг", "ping"]:
        await message.channel.send("Понг! 🏓 Я на связи!")
    elif content in ["кто лох", "кто лох дня"]:
        ctx = await bot.get_context(message)
        await who_lox(ctx)
    elif content in ["команды", "помощь", "хелп", "help"]:
        ctx = await bot.get_context(message)
        await help(ctx)

    await bot.process_commands(message)

@bot.event
async def on_ready():
    await start_web_server()
    print(f"✅ Бот {bot.user} успешно запустился!")
    if not schedule_checker.is_running():
        schedule_checker.start()

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📖 Справочник Асы Митаки",
        description="Вот список доступных команд:",
        color=discord.Color.from_rgb(138, 43, 226),
    )
    embed.add_field(
        name="📻 Радио Асы (Музыка в войсе)",
        value=(
            "`!radio` — включить или выключить радио в голосовом канале\n"
            "`!skip` — пропустить текущий трек\n"
            "`!volume 50` — изменить громкость (от 0 до 100)\n"
            "`!stop_radio` — принудительно выключить радио и отключить бота"
        ),
        inline=False,
    )
    embed.add_field(
        name="💬 Общение и статистика",
        value=(
            "`!mystats` — твоя статистика игр и времени в войсе\n"
            "`!top_games` — топ игроков\n"
            "`!top_voice` — топ по времени в войсе\n"
            "`!who_lox` — узнать Лоха дня"
        ),
        inline=False,
    )
    await ctx.send(embed=embed)

@bot.command(name="mystats")
async def my_stats(ctx):
    user_id = ctx.author.id
    cursor.execute("SELECT game, total_seconds FROM game_stats WHERE user_id = ? ORDER BY total_seconds DESC", (user_id,))
    games = cursor.fetchall()
    cursor.execute("SELECT total_seconds FROM voice_stats WHERE user_id = ?", (user_id,))
    voice_row = cursor.fetchone()
    voice_seconds = voice_row[0] if voice_row else 0

    description = f"🎙️ **В голосовых каналах:** {format_seconds(voice_seconds)}\n🕹️ **Игровая активность:**\n"
    if games:
        for game, sec in games:
            description += f"• **{game}**: {format_seconds(sec)}\n"
    else:
        description += "Данных пока нет."

    embed = discord.Embed(title=f"📊 Статистика {ctx.author.display_name}", description=description, color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command(name="top_games")
async def top_games(ctx):
    cursor.execute("SELECT user_id, game, total_seconds FROM game_stats ORDER BY total_seconds DESC LIMIT 10")
    results = cursor.fetchall()
    if not results:
        await ctx.send("Статистика по играм пока пуста.")
        return
    description = "".join([f"{idx}. <@{u_id}> — **{game}**: {format_seconds(sec)}\n" for idx, (u_id, game, sec) in enumerate(results, 1)])
    await ctx.send(embed=discord.Embed(title="🏆 Топ игроков", description=description, color=discord.Color.gold()))

@bot.command(name="top_voice")
async def top_voice(ctx):
    cursor.execute("SELECT user_id, total_seconds FROM voice_stats ORDER BY total_seconds DESC LIMIT 10")
    results = cursor.fetchall()
    if not results:
        await ctx.send("Статистика войса пуста.")
        return
    description = "".join([f"{idx}. <@{u_id}> — {format_seconds(sec)}\n" for idx, (u_id, sec) in enumerate(results, 1)])
    await ctx.send(embed=discord.Embed(title="🎙️ Топ по голосовым каналам", description=description, color=discord.Color.green()))

@bot.command()
async def who_lox(ctx):
    global current_lox_of_the_day
    if current_lox_of_the_day is None:
        current_lox_of_the_day = random.choice(LOX_DAY)
    await ctx.send(embed=discord.Embed(title="🔍 Кто сегодня лох?", description=f"{current_lox_of_the_day}", color=discord.Color.dark_red()))

if __name__ == "__main__":
    bot.run(TOKEN)