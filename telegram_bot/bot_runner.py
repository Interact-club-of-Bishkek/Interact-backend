import os
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# ---------- setup ----------
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")


# ---------- routers ----------
try:
    from crocodile.crocodile_runner import crocodile_router, manager as crocodile_manager
except Exception:
    crocodile_router = Router()
    crocodile_manager = None

try:
    from mafia.handlers import mafia_router
except Exception:
    mafia_router = Router()

from general.handlers import general_router
from volunteers.telegram_handlers import application_router
from volunteers.project_creation import router as project_creation_router


async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    if not TOKEN:
        logging.error("BOT_TOKEN not found")
        return

    # ✅ SIMPLE + STABLE BOT (no custom session)
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    dp = Dispatcher()

    # inject bot if needed
    if crocodile_manager:
        crocodile_manager.bot = bot

    # routers
    dp.include_router(application_router)
    dp.include_router(project_creation_router)
    dp.include_router(general_router)
    dp.include_router(crocodile_router)
    dp.include_router(mafia_router)

    try:
        logging.info("🚀 Bot starting...")

        # safe webhook cleanup
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception as e:
            logging.warning(f"Webhook warning: {e}")

        logging.info("📡 Polling started")
        await dp.start_polling(bot)

    finally:
        await bot.session.close()
        logging.info("🧹 Session closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Stopped manually")
    except Exception as e:
        logging.exception(f"Fatal error: {e}")
        raise