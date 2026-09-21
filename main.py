import datetime
import os
import random
import re
from aiohttp import web
import discord
from google.genai import types
from google import genai
from discord.ext import commands, tasks
from dotenv import load_dotenv

# 1. Загружаем токен из файла .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Инициализируем клиент Gemini
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ⚠️ УКАЖИ ID СВОЕГО ТЕКСТОВОГО КАНАЛА
CHANNEL_ID = 1424321634935902302

# ⚠️ НАСТРОЙ ВРЕМЯ ОТПРАВКИ (Часы, Минуты)
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


# 🌐 Мини веб-сервер для Render Web Service
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


# Фоновая задача: Спокойной ночи
@tasks.loop(time=NIGHT_TIME)
async def send_night_wish():
  channel = bot.get_channel(CHANNEL_ID)
  if channel:
    embed = discord.Embed(
        title="🌙 Время спать!",
        description=(
            "Всем спокойной ночи и приятных снов! 😴✨\nНа сегодня отбой,"
            " отдыхайте!"
        ),
        color=discord.Color.dark_blue(),
    )
    await channel.send(embed=embed)


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


# 🤖 Обработчик всех входящих сообщений
@bot.event
async def on_message(message):
  if message.author.bot:
    return

  content = message.content.lower().strip()
  
  
  # 🤖 Проверка: если в сообщении упоминается Аса
  if "аса" in content:
        async with message.channel.typing():  # Покажет статус "Аса печатает..."
            try:
                # Очищаем текст от самого слова "аса", чтобы отправить ИИ только вопрос
                user_prompt = re.sub(r'\bаса\b', '', message.content, flags=re.IGNORECASE).strip()
                if not user_prompt:
                    user_prompt = "Привет!"

                response = gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        # Задаем характер Асы через системную инструкцию
                        system_instruction="Ты — Аса, дерзкая, немного ироничная, но полезная ассистентка в Discord сервере. Отвечай кратко и емко."
                    )
                )
                await message.channel.send(response.text)
                return  # Завершаем, чтобы не срабатывали обычные текстовые реакции
            except Exception as e:
                print(f"Ошибка ИИ: {e}")
                await message.channel.send("Ой, у меня мозги закипели... Попробуй еще раз чуть позже!")
  
  
  
  
  
  
  if content in ["Павленко", "Павлин", "павленко", "павлик"]:
          image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQerancTqr09xw6t5XFwvR2KF40aWWbKZJRqtjwm8zDO1dJJy_mh23bzNg4&s=10"
          
          embed = discord.Embed()
          embed.set_image(url=image_url)
          await message.channel.send(embed=embed)
  
  if content in ["Черт", "Тимофей", "черт", "тимофей"]:
        image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTQ1mEIM5wxh0rbz5OVGQx8jaAmNk1x8CHO88R68uJFbM4d1p0NkZoIePT3&s=10"
        
        embed = discord.Embed()
        embed.set_image(url=image_url)
        await message.channel.send(embed=embed)
  
  
  if content in ["Костя", "Костон", "костя",]:
          image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTqnSH8VhvNVZN3dFYYMUxMFKH21OgmzvOFJYFDpehJp2AS7SU9erk1TPM&s=10"
          
          embed = discord.Embed()
          embed.set_image(url=image_url)
          await message.channel.send(embed=embed)
  
  
  if content in ["Хвеся", "хвеся", "хвелий", "Хвелий"]:
        image_url = "https://external-preview.redd.it/keeper-of-the-light-on-a-scooter-d-v0-DY9_rZ0Ou6mPZABRBPEd49IYniTdHiEaXcZ9aiDasdY.jpg?format=pjpg&auto=webp&s=3429da530924a1f41f3ec5283113b60fcdbb3d1b"
        
        embed = discord.Embed()
        embed.set_image(url=image_url)
        await message.channel.send(embed=embed)
  
  
  if content in ["Даня", "даня"]:
      image_url = "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/37/Oryctolagus_cuniculus_Tasmania_2.jpg/960px-Oryctolagus_cuniculus_Tasmania_2.jpg?utm_source=ru.wikipedia.org&utm_campaign=index&utm_content=thumbnail"
      
      embed = discord.Embed()
      embed.set_image(url=image_url)
      await message.channel.send(embed=embed)
  
  
  if content in ["Луцук", "луцук"]:
      image_url = "https://pmgroupkz.s3.eu-north-1.amazonaws.com/uploads/esquire/2019/10/dia-de-la-risa-1024x682.jpg"
      
      embed = discord.Embed()
      embed.set_image(url=image_url)
      await message.channel.send(embed=embed)
      

      

  if content in [
      "пинг",
      "ping",
      "Ping",
      "Пинг",
      "!ping",
      "!пинг",
  ]:
    await message.channel.send("Понг! 🏓 Я на связи и всё слышу!")

  elif "аса" in content and "привет" in content:
    await message.channel.send(f"Привет, {message.author.mention}! 👋")

  elif content in ["кто лох", "кто лох дня"]:
    ctx = await bot.get_context(message)
    await who_lox(ctx)

  if content in ["команды", "помощь", "хелп", "help"]:
    ctx = await bot.get_context(message)
    await help(ctx)

  await bot.process_commands(message)


@bot.event
async def on_ready():
  await start_web_server()
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

  if not send_night_wish.is_running():
    send_night_wish.start()
    print(
        "⏰ Фоновая задача 'Спокойной ночи' запущена на"
        f" {NIGHT_TIME.strftime('%H:%M')}!"
    )


# 📜 Команда помощи
@bot.command()
async def help(ctx):
  embed = discord.Embed(
      title="📖 Список команд Асы",
      description=(
          "Привет! Я **Аса** 🗡️. Вот список всех доступных команд и функций,"
          " которые я умею выполнять на сервере:"
      ),
      color=discord.Color.from_rgb(138, 43, 226),
  )

  embed.add_field(
      name="💬 Основные команды",
      value=(
          "`!ping` или `пинг` — проверить, на связи ли Аса\n"
          "`!track` — получить случайный музыкальный трек\n"
          "`!who_lox` или `кто лох` — узнать, кто сегодня выбран Лохом дня"
      ),
      inline=False,
  )

  embed.add_field(
      name="⏰ Автоматические события",
      value=(
          "☀️ **10:00** — Утренняя рекомендация трека дня\n"
          "🦆 **18:00** — Выбор «Лоха дня» с перевыдачей специальной роли\n"
          "🌙 **23:50** — Пожелание спокойной ночи"
      ),
      inline=False,
  )

  embed.set_footer(
      text=f"Запросил: {ctx.author.display_name}",
      icon_url=(
          ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
      ),
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
  
   # =========================================================




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