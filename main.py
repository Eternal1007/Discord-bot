import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# 1. Загружаем токен из файла .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# 2. Настраиваем права бота (разрешаем читать сообщения в чате)
intents = discord.Intents.default()
intents.message_content = True

# 3. Создаем бота с префиксом ! (команды будут начинаться с !)
bot = commands.Bot(command_prefix="!", intents=intents)


# 4. Событие: сработает, когда бот успешно подключится к Discord
@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} успешно запустился и вышел в сеть!")


# 5. Тестовая команда !ping
@bot.command()
async def ping(ctx):
    # ctx (context) — это информация о том, кто и где вызвал команду
    await ctx.send("Понг! 🏓 Бот на связи и всё работает!")


# 6. Запуск бота
if __name__ == "__main__":
    bot.run(TOKEN)