# bot_runner.py
import os
import asyncio
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

# Загрузка токена
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(TOKEN)
dp = Dispatcher()

# ---------- Импорт ваших игр ----------
# Крокодил
from crocodile.crocodile_runner import crocodile_router  # теперь это Router
from crocodile.crocodile_game import CrocodileManager

# Мафия
from mafia.bot import register_mafia_handlers

# ---------- Инициализация игр ----------
# Крокодил
manager = CrocodileManager()
manager.bot = bot
dp.include_router(crocodile_router)  # <-- подключаем Router

# Мафия
register_mafia_handlers(dp, bot)  # все обработчики мафии тоже подключаются к dp

# ---------- Запуск ----------
async def main():
    print("[INFO] Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
