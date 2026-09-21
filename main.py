import asyncio
import datetime
import os
import random
import re
from aiohttp import web
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

# 1. Загружаем токен из файла .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
print("KEY:", GEMINI_KEY[:5] if GEMINI_KEY else None)

# Инициализируем клиент Gemini с явной передачей ключа
gemini_client = genai.Client(api_key=GEMINI_KEY)

# ⚠️ УКАЖИ ID СВОЕГО ТЕКСТОВОГО КАНАЛА
CHANNEL_ID = 1424321634935902302

# ⚠️ НАСТРОЙ ВРЕМЯ ОТПРАВКИ
DAILY_TIME = datetime.time(hour=10, minute=0, second=0)
LOX_TIME = datetime.time(hour=18, minute=0, second=0)
NIGHT_TIME = datetime.time(hour=23, minute=0, second=0)

# Глобальные переменные для хранения лоха дня
current_lox_of_the_day = None
current_lox_member = None

# Настройка прав и инициализация бота
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")  # Отключаем встроенный help

ROLE_LOX_ID = 1551560593771864154

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
    "[PHARAOH - Unplugged 2: Love Kills (feat. White Punk) 🎧](https://open.spotify.com/track/6b3LmsVYOMnGIpIbxW1WEW?si=1f4cafba56b344c0)",
    "[PHARAOH - ФОСФОР 🎤](https://open.spotify.com/track/2qGhxo0FWYAWZhRGYfOQCO?si=c2bb728f7cfb407c)",
    "[Ooes - Зима ❄️](https://open.spotify.com/track/0cOftxEWGyu4XAqEsqmdWS?si=5deba0586639473c)",
    "[The Neighbourhood - Sweater Weather](https://open.spotify.com/track/2QjOHCTQ1Jl3zawyYOpxh6?si=13dc3b89a81e4329)",
    "[Scally Milano&uglystphan - Вампир 🎤](https://open.spotify.com/track/7p62Jtx8nlvgQXYawhzIcI?si=d61962ae50034af4)",
]


# 🌐 Мини веб-сервер для Render
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


# Фоновые задачи
@tasks.loop(time=NIGHT_TIME)
async def send_night_wish():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🌙 Время спать!",
            description="Всем спокойной ночи и приятных снов! 😴✨\nНа сегодня отбой, отдыхайте!",
            color=discord.Color.dark_blue(),
        )
        await channel.send(embed=embed)


@tasks.loop(time=LOX_TIME)
async def send_daily_lox():
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
                print("Не удалось выдать роль (проверь иерархию ролей)")

    embed = discord.Embed(
        title="🦆 Лох дня!",
        description=(
            f"🤡 ИТОГИ ДНЯ!:\n💀 **{current_lox_of_the_day}**\n\n🎭 *Роль"
            f" {role.mention if role else 'Лох дня'} официально переходит победителю!*"
        ),
        color=discord.Color.red(),
    )
    await channel.send(embed=embed)


@tasks.loop(time=DAILY_TIME)
async def send_daily_track():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        song = random.choice(TRACKS_LIST)
        embed = discord.Embed(
            title="☀️ Доброе утро! Трек дня!",
            description=f"Сегодняшняя рекомендация:\n🎶 **{song}**",
            color=discord.Color.gold(),
        )
        await channel.send(embed=embed)


# 🤖 Обработчик входящих сообщений
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower().strip()

    # 🤖 Проверка: если в сообщении упоминается Аса
    if "аса" in content:
        async with message.channel.typing():
            try:
                user_prompt = re.sub(
                    r"\bаса\b", "", message.content, flags=re.IGNORECASE
                ).strip()
                if not user_prompt:
                    user_prompt = "Привет!"

                def get_gemini_response():
                    system_instruction = "Ты — Аса, дерзкая, немного ироничная, но полезная ассистентка в Discord сервере. Отвечай кратко и емко."
                    config = types.GenerateContentConfig(
                        system_instruction=system_instruction,
                    )

                    # 🔁 Повторяем запрос при временной перегрузке Gemini (503)
                    max_retries = 3
                    delay_seconds = 2
                    last_error = None

                    for attempt in range(1, max_retries + 1):
                        try:
                            return gemini_client.models.generate_content(
                                model="gemini-3.6-flash",
                                contents=user_prompt,
                                config=config,
                            )
                        except genai_errors.ServerError as e:
                            last_error = e
                            if "503" in str(e) or "UNAVAILABLE" in str(e):
                                print(
                                    f"⚠️ Gemini перегружен (попытка {attempt}/{max_retries}), жду {delay_seconds}с..."
                                )
                                if attempt < max_retries:
                                    import time
                                    time.sleep(delay_seconds)
                                continue
                            raise

                    raise last_error

                response = await asyncio.to_thread(get_gemini_response)

                if response and response.text:
                    await message.channel.send(response.text)
                    return
            except Exception as e:
                import traceback
                print(f"❌ Ошибка ИИ Gemini: {e}")
                traceback.print_exc()
                await message.channel.send(
                    "Ой, у меня мозги закипели... Попробуй еще раз чуть позже!"
                )
                return

    # 🖼️ Картинки-реакции
    if content in ["павленко", "павлин", "павлик"]:
        image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQerancTqr09xw6t5XFwvR2KF40aWWbKZJRqtjwm8zDO1dJJy_mh23bzNg4&s=10"
        embed = discord.Embed().set_image(url=image_url)
        await message.channel.send(embed=embed)

    elif content in ["черт", "тимофей"]:
        image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTQ1mEIM5wxh0rbz5OVGQx8jaAmNk1x8CHO88R68uJFbM4d1p0NkZoIePT3&s=10"
        embed = discord.Embed().set_image(url=image_url)
        await message.channel.send(embed=embed)

    elif content in ["костя", "костон"]:
        image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTqnSH8VhvNVZN3dFYYMUxMFKH21OgmzvOFJYFDpehJp2AS7SU9erk1TPM&s=10"
        embed = discord.Embed().set_image(url=image_url)
        await message.channel.send(embed=embed)

    elif content in ["хвеся", "хвелий"]:
        image_url = "https://external-preview.redd.it/keeper-of-the-light-on-a-scooter-d-v0-DY9_rZ0Ou6mPZABRBPEd49IYniTdHiEaXcZ9aiDasdY.jpg?format=pjpg&auto=webp&s=3429da530924a1f41f3ec5283113b60fcdbb3d1b"
        embed = discord.Embed().set_image(url=image_url)
        await message.channel.send(embed=embed)

    elif content in ["даня"]:
        image_url = "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/37/Oryctolagus_cuniculus_Tasmania_2.jpg/960px-Oryctolagus_cuniculus_Tasmania_2.jpg?utm_source=ru.wikipedia.org&utm_campaign=index&utm_content=thumbnail"
        embed = discord.Embed().set_image(url=image_url)
        await message.channel.send(embed=embed)

    elif content in ["луцук"]:
        image_url = "https://pmgroupkz.s3.eu-north-1.amazonaws.com/uploads/esquire/2019/10/dia-de-la-risa-1024x682.jpg"
        embed = discord.Embed().set_image(url=image_url)
        await message.channel.send(embed=embed)

    # 💬 Текстовые команды
    elif content in ["пинг", "ping", "!ping", "!пинг"]:
        await message.channel.send("Понг! 🏓 Я на связи и всё слышу!")

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

    if not send_daily_track.is_running():
        send_daily_track.start()

    if not send_daily_lox.is_running():
        send_daily_lox.start()

    if not send_night_wish.is_running():
        send_night_wish.start()


@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📖 Список команд Асы",
        description="Привет! Я **Аса** 🗡️. Вот список всех доступных команд:",
        color=discord.Color.from_rgb(138, 43, 226),
    )
    embed.add_field(
        name="💬 Основные команды",
        value="`!ping` или `пинг` — проверить, на связи ли Аса\n`!track` — получить случайный трек\n`!who_lox` или `кто лох` — узнать Лоха дня",
        inline=False,
    )
    await ctx.send(embed=embed)


@bot.command()
async def who_lox(ctx):
    global current_lox_of_the_day
    if current_lox_of_the_day is None:
        current_lox_of_the_day = random.choice(LOX_DAY)

    embed = discord.Embed(
        title="🔍 ПЕРЕПРОВЕРКА: Кто сегодня лох?",
        description=f"Напоминаю, титул зафиксирован:\n\n{current_lox_of_the_day}",
        color=discord.Color.dark_red(),
    )
    await ctx.send(embed=embed)


@bot.command()
async def ping(ctx):
    await ctx.send("Понг! 🏓 Я на связи и всё работает!")


@bot.command()
async def track(ctx):
    song = random.choice(TRACKS_LIST)
    embed = discord.Embed(
        title="🎵 Случайный трек",
        description=f"Рекомендация для тебя:\n🎶 **{song}**",
        color=discord.Color.purple(),
    )
    await ctx.send(embed=embed)


if __name__ == "__main__":
    bot.run(TOKEN)