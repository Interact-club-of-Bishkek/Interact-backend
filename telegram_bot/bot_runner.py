import os
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, Router
# Импорт для корректной инициализации бота (Aiogram 3.7+)
from aiogram.client.default import DefaultBotProperties 
from dotenv import load_dotenv

# Убедимся, что Python видит родительскую папку для импорта модулей
# Это помогает избежать ModuleNotFoundError при сложном запуске
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ---------- Импорт роутеров ----------
# Используем try-except для стабильности при отсутствии игровых модулей
try:
    from crocodile.crocodile_runner import crocodile_router, manager as crocodile_manager
except ImportError as e:
    logging.warning(f"Не удалось импортировать Крокодила: {e}")
    crocodile_router = Router() 
    crocodile_manager = None

try:
    from mafia.handlers import mafia_router 
except ImportError as e:
    logging.warning(f"Не удалось импортировать Мафию: {e}")
    mafia_router = Router()

# --- Главные роутеры ---
# Предполагаем, что эти модули существуют и находятся на нужном пути
from general.handlers import general_router 
from volunteers.telegram_handlers import application_router 

# ---------- Загрузка конфига ----------
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    if not TOKEN:
        logging.error("[ERROR] Токен не найден! Проверьте файл .env")
        return

    # 1. Инициализация ЕДИНСТВЕННОГО бота
    # !!! ИСПРАВЛЕНИЕ: Используем DefaultBotProperties для parse_mode="HTML" (Aiogram 3.7+)
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher()

    # 2. Передаем этого бота в менеджер крокодила
    if crocodile_manager:
        try:
            crocodile_manager.bot = bot
        except Exception as e:
            logging.warning(f"Ошибка при передаче бота в crocodile_manager: {e}")

    # 3. Подключение роутеров (FSM ПЕРВЫМ)
    dp.include_router(application_router) # <-- FSM (анкеты)
    dp.include_router(general_router) 
    
    # Подключаем игровые роутеры
    dp.include_router(crocodile_router)
    dp.include_router(mafia_router)

    logging.info("[INFO] Бот запущен...")
    # Удаляем ожидающие обновления и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен")
    except Exception as e:
        logging.critical(f"Критическая ошибка запуска: {e}")