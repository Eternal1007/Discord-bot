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
# Нажми ПКМ по нужному текстовому каналу в Discord -> Скопировать ID канала
CHANNEL_ID =  1424321634935902302 # Замени эти цифры на реальный ID канала!

# ⚠️ НАСТРОЙ ВРЕМЯ ОТПРАВКИ (Часы, Минуты)
# Например, hour=10, minute=0 означает 10:00 утра по времени твоего ПК/сервера
DAILY_TIME = datetime.time(hour=10, minute=0, second=0)

# Список треков (можно добавлять названия или прямые ссылки на YouTube/Spotify)
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


# 3. Фоновая задача для ежедневного трека
@tasks.loop(time=DAILY_TIME)
async def send_daily_track():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        song = random.choice(TRACKS_LIST)
        embed = discord.Embed(
            title="☀️ Доброе утро! Трек дня!",
            description=f"Сегодняшняя рекомендация:\n🎶 **{song}**",
            color=discord.Color.gold()
        )
        await channel.send(embed=embed)


# 4. Событие старта бота
@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} успешно запустился!")
    # Запускаем ежедневный цикл
    if not send_daily_track.is_running():
        send_daily_track.start()
        print(f"⏰ Фоновая задача 'Трек дня' запущена на {DAILY_TIME.strftime('%H:%M')}!")


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
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)


# 7. Запуск бота
if __name__ == "__main__":
    bot.run(TOKEN)
#command  list:!ping, !track
#for start:python main.py
    