import datetime
import os
import random
import re
from aiohttp import web
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# 1. Загружаем токен из файла .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ⚠️ УКАЖИ ID СВОЕГО ТЕКСТОВОГО КАНАЛА
CHANNEL_ID = 1424321634935902302

# ⚠️ НАСТРОЙ ВРЕМЯ ОТПРАВКИ (Часы, Минуты)
DAILY_TIME = datetime.time(hour=10, minute=0, second=0)
LOX_TIME = datetime.time(hour=18, minute=0, second=0)
NIGHT_TIME = datetime.time(hour=23, minute=0, second=0)

# Глобальные переменные для хранения лоха дня
current_lox_of_the_day = None
current_lox_member = None

LOX_DAY = [
    (
        "Сегодня главный Лох Хвелий(Велий) Ярослав Юджинович"
        "<@1266287283447791709>"
    ),
    "Главный лох на сегодня Властелин Костя(Смех владыки)<@998569440432095253>",
    "Сегодня главный лох Тимочерт(Сын моржа)<@857923827346046977>",
    (
        "Сегодня главный ЛОШАРА это Даня кролик(Смех Предворного шута)"
        "<@1317437941743878248>"
    ),
    "Лохушка на сегодня это Маша(Барни будет плакать)<@1309448666918158347>",
    (
        "Главный лох на сегодня это Влад(У тебя слабый рейджин и 0 ауры)"
        "<@1168095961415962624>"
    ),
    (
        "Лошарище местный сегодня это Павлин Артем(Марина Китоглав)"
        "<@952601502395011142>"
    ),
]

# Список треков со ссылками
TRACKS_LIST = [
    (
        "[Nirvana - Lounge Act"
        " 🎸](https://open.spotify.com/track/1o5jmMhhk2UZ9YP1X5fXfj?si=49a4e9ad37e24c2a)"
    ),
    (
        "[Nirvana - Drain You"
        " 🎸](https://open.spotify.com/track/0bTLGlCqwZXwJGWGE2Dywg?si=f775e73a88b64f23)"
    ),
    (
        "[Nirvana - SLIVER"
        " 🎸](https://open.spotify.com/track/3BtHClmMmURD8UHF2fiyxt?si=a87e8604f6064a2d)"
    ),
    (
        "[PHARAOH - Smart"
        " 🎤](https://open.spotify.com/track/2zLss6D2YVa4wsqpsqYkkW?si=6866c7605598414d)"
    ),
    (
        "[Boulevard Depo - Hot Wheels"
        " 🎤](https://open.spotify.com/track/6ustl54iGfVeK8J10EnUem?si=402ac404bb0a49b3)"
    ),
    (
        "[Пошлая Молли - Молли"
        " ⚡](https://open.spotify.com/track/27eSRcPFnKfaufCgr33aAr?si=d64b868330434c1f)"
    ),
    (
        "[Avril Lavigne - Sk8er Boi"
        " 🛹](https://open.spotify.com/track/00Mb3DuaIH1kjrwOku9CGU?si=858c3912dc434ff3)"
    ),
    (
        "[PHARAOH - Unplugged 2: Love Kills (feat. White Punk)"
        "🎧](https://open.spotify.com/track/6b3LmsVYOMnGIpIbxW1WEW?si=1f4cafba56b344c0)"
    ),
    (
        "[PHARAOH - ФОСФОР"
        " 🎤](https://open.spotify.com/track/2qGhxo0FWYAWZhRGYfOQCO?si=c2bb728f7cfb407c)"
    ),
    (
        "[Ooes - Зима"
        " ❄️](https://open.spotify.com/track/0cOftxEWGyu4XAqEsqmdWS?si=5deba0586639473c)"
    ),
    (
        "[The Neighbourhood - Sweater"
        " Weather](https://open.spotify.com/track/2QjOHCTQ1Jl3zawyYOpxh6?si=13dc3b89a81e4329)"
    ),
    (
        "[Scally Milano&uglystphan - Вампир"
        " 🎤](https://open.spotify.com/track/7p62Jtx8nlvgQXYawhzIcI?si=d61962ae50034af4)"
    ),
]

# 🌐 Мини веб-сервер для поддержки работы Render Web Service
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


# 2. Настраиваем права бота
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

ROLE_LOX_ID = 1551560593771864154


# Фоновая задача: Лох дня (18:00)
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
          f" {role.mention if role else 'Лох дня'} официально переходит"
          " победителю!*"
      ),
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


# 3. Событие старта бота
@bot.event
async def on_ready():
  await start_web_server()  # Запускаем портал для Render
  print(f"✅ Бот {bot.user} успешно запустился!")

  if not send_daily_track.is_running():
    send_daily_track.start()
    print(
        "⏰ Фоновая задача 'Трек дня' запущена на"
        f" {DAILY_TIME.strftime('%H:%M')}!"
    )

  if not send_daily_lox.is_running():
    send_daily_lox.start()
    print(
        f"⏰ Фоновая задача 'Лох дня' запущена на {LOX_TIME.strftime('%H:%M')}!"
    )


# 4. Команды бота
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