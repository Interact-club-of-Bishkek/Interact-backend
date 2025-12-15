import os
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

# ---------- Импорт роутеров ----------
# Импортируем роутер И объект manager, чтобы передать ему бота
from crocodile.crocodile_runner import crocodile_router, manager as crocodile_manager
from mafia.handlers import mafia_router 
# ❗ НОВЫЙ ИМПОРТ ❗
from general.handlers import general_router 

# ---------- Загрузка конфига ----------
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    if not TOKEN:
        print("[ERROR] Токен не найден! Проверьте файл .env")
        return

    # 1. Инициализация ЕДИНСТВЕННОГО бота
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # 2. Передаем этого бота в менеджер крокодила
    crocodile_manager.bot = bot 

    # 3. Подключение роутеров
    # ❗ ВАЖНО: general_router должен быть первым, чтобы ловить /start в ЛС
    dp.include_router(general_router) 
    dp.include_router(crocodile_router)
    dp.include_router(mafia_router)

    print("[INFO] Бот запущен...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")