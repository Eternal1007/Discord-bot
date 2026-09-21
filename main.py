import os
import random
import datetime
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# 1. Загружаем токен из файла .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ⚠️ УКАЖИ ID СВОЕГО ТЕКСТОВОГО КАНАЛА (куда бот будет слать трек)
CHANNEL_ID = 1424321634935902302

# ⚠️ НАСТРОЙ ВРЕМЯ ОТПРАВКИ (Часы, Минуты)
DAILY_TIME = datetime.time(hour=10, minute=0, second=0)
LOX_TIME = datetime.time(hour=18, minute=0, second=0)

# Глобальная переменная для хранения текущего "лоха дня"
current_lox_of_the_day = None

LOX_DAY = [
    "Сегодня главный Лох Хвелий(Велий) Ярослав Юджинович<@1266287283447791709>",
    "Главный лох на сегодня Властелин Костя(Смех владыки)<@998569440432095253>",
    "Сегодня главный лох Тимочерт(Сын моржа)<@857923827346046977>",
    "Сегодня главный ЛОШАРА это Даня кролик(Смех Предворного шута)<@1317437941743878248>",
    "Лохушка на сегодня это Маша(Барни будет плакать)<@1309448666918158347>",
    "Главный лох на сегодня это Влад(У тебя слабый рейджин и 0 ауры)<@1168095961415962624>",
    "Лошарище местный сегодня это Павлин Артем(Марина Китоглав)<@952601502395011142>",
]

# Список треков со ссылками
TRACKS_LIST = [
    "[Nirvana - Lounge Act 🎸](https://open.spotify.com/track/1o5jmMhhk2UZ9YP1X5fXfj?si=49a4e9ad37e24c2a)",
    "[Nirvana - Drain You 🎸](https://open.spotify.com/track/0bTLGlCqwZXwJGWGE2Dywg?si=f775e73a88b64f23)",
    "[Nirvana - SLIVER 🎸](https://open.spotify.com/track/3BtHClmMmURD8UHF2fiyxt?si=a87e8604f6064a2d)",
    "[PHARAOH - Smart 🎤](https://open.spotify.com/track/2zLss6D2YVa4wsqpsqYkkW?si=6866c7605598414d)",
    "[Boulevard Depo - Hot Wheels 🎤](https://open.spotify.com/track/6ustl54iGfVeK8J10EnUem?si=402ac404bb0a49b3)",
    "[Пошлая Молли - Молли ⚡](https://open.spotify.com/track/27eSRcPFnKfaufCgr33aAr?si=d64b868330434c1f)",
    "[Avril Lavigne - Sk8er Boi 🛹](https://open.spotify.com/track/00Mb3DuaIH1kjrwOku9CGU?si=858c3912dc434ff3)",
    "[PHARAOH - Unplugged 2: Love Kills (feat. White Punk)🎧](https://open.spotify.com/track/6b3LmsVYOMnGIpIbxW1WEW?si=1f4cafba56b344c0)",
    "[PHARAOH - ФОСФОР 🎤](https://open.spotify.com/track/2qGhxo0FWYAWZhRGYfOQCO?si=c2bb728f7cfb407c)",
    "[Ooes - Зима ❄️](https://open.spotify.com/track/0cOftxEWGyu4XAqEsqmdWS?si=5deba0586639473c)",
    "[The Neighbourhood - Sweater Weather](https://open.spotify.com/track/2QjOHCTQ1Jl3zawyYOpxh6?si=13dc3b89a81e4329)",
    "[Scally Milano&uglystphan - Вампир 🎤](https://open.spotify.com/track/7p62Jtx8nlvgQXYawhzIcI?si=d61962ae50034af4)",
]

# 2. Настраиваем права бота
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# Фоновая задача: Лох дня (18:00)
@tasks.loop(time=LOX_TIME)
async def send_daily_lox():
    global current_lox_of_the_day
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        current_lox_of_the_day = random.choice(LOX_DAY)
        embed = discord.Embed(
            title="🦆 Лох дня!",
            description=f"🤡 ИТОГИ ДНЯ!:\n💀 **{current_lox_of_the_day}**",
            color=discord.Color.red(),
        )
        await channel.send(embed=embed)


# Фоновая задача: Трек дня (10:00)
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


# 3. Единственное событие старта бота
@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} успешно запустился!")

    if not send_daily_track.is_running():
        send_daily_track.start()
        print(f"⏰ Фоновая задача 'Трек дня' запущена на {DAILY_TIME.strftime('%H:%M')}!")

    if not send_daily_lox.is_running():
        send_daily_lox.start()
        print(f"⏰ Фоновая задача 'Лох дня' запущена на {LOX_TIME.strftime('%H:%M')}!")


# 4. Команда !who_lox для перепроверки
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


# 5. Команда !ping для проверки
@bot.command()
async def ping(ctx):
    await ctx.send("Понг! 🏓 Бот на связи и всё работает!")


# 6. Команда !track для получения случайного трека вручную
@bot.command()
async def track(ctx):
    song = random.choice(TRACKS_LIST)
    embed = discord.Embed(
        title="🎵 Случайный трек",
        description=f"Рекомендация для тебя:\n🎶 **{song}**",
        color=discord.Color.purple(),
    )
    await ctx.send(embed=embed)


# 7. Запуск бота
if __name__ == "__main__":
    bot.run(TOKEN)

# =========================================================
# 📜 ПОЛЕЗНЫЕ ЗАМЕТКИ ДЛЯ РАЗРАБОТКИ
# =========================================================
#
# 🤖 Список команд в Discord:
#   !ping    - Проверка работы бота
#   !track   - Случайный трек прямо сейчас
#   !who_lox - Перепроверить, кто сегодня лох
#
# 🚀 Запуск бота в терминале:
#   python main.py
#
# 🐙 Полезные команды для GitHub:
#   git add .
#   git commit -m "Твое сообщение"
#   git push
# =========================================================