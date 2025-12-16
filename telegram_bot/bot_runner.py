import os
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

# ---------- Импорт роутеров ----------
from crocodile.crocodile_runner import crocodile_router, manager as crocodile_manager
from mafia.handlers import mafia_router 
from general.handlers import general_router 
from volunteers.telegram_handlers import application_router 

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

    # 2. Передаем этого бота в менеджер крокодила (если нужно)
    try:
        crocodile_manager.bot = bot 
    except NameError:
        pass # Игнорируем, если crocodile_manager не определен

    # 3. Подключение роутеров (FSM ПЕРВЫМ)
    dp.include_router(application_router) # <-- ЛОВИТ 'volunteer_apply'
    dp.include_router(general_router)    # <-- ЛОВИТ /start и 'ai_assistant'
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