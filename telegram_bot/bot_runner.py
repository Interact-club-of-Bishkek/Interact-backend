import os
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

from dotenv import load_dotenv

# ---------- путь ----------
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ---------- роутеры ----------
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

from general.handlers import general_router
from volunteers.telegram_handlers import application_router
from volunteers.project_creation import router as project_creation_router

# ---------- env ----------
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# ---------- session ----------
session = AiohttpSession(timeout=60)


async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    if not TOKEN:
        logging.error("❌ BOT_TOKEN не найден в .env")
        return

    bot = Bot(
        token=TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    dp = Dispatcher()

    try:
        # передача бота в менеджер
        if crocodile_manager:
            crocodile_manager.bot = bot

        # роутеры
        dp.include_router(application_router)
        dp.include_router(project_creation_router)
        dp.include_router(general_router)
        dp.include_router(crocodile_router)
        dp.include_router(mafia_router)

        logging.info("🚀 Бот запущен...")

        # webhook cleanup
        logging.info("Удаляем webhook...")
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception as e:
            logging.warning(f"Webhook warning: {e}")

        logging.info("Webhook удалён")

        # polling
        logging.info("Запуск polling...")
        await dp.start_polling(bot)

    finally:
        # важно закрывать session
        await bot.session.close()
        logging.info("Session закрыта")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен")
    except Exception as e:
        logging.exception(f"Критическая ошибка запуска: {e}")
        raise