import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from pathlib import Path
import json
import random

from crocodile.crocodile_game import CrocodileManager

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(TOKEN)
dp = Dispatcher()

manager = CrocodileManager()
manager.bot = bot  # для таймера

BASE_DIR = Path(__file__).resolve().parent
LEVELS_FILE = BASE_DIR / "words_by_level.json"  # JSON с уровнями

# ---------- КНОПКИ ----------

def kb_start() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👀 Посмотреть слово", callback_data="view_word")],
            [InlineKeyboardButton(text="🔄 Поменять слово", callback_data="change_word")]
        ]
    )

def kb_leader() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Хочу быть ведущим", callback_data="want_leader")]
        ]
    )

def kb_level_selection() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Лёгкий", callback_data="level_easy"),
                InlineKeyboardButton(text="🟡 Средний", callback_data="level_medium"),
                InlineKeyboardButton(text="🔴 Тяжёлый", callback_data="level_hard")
            ]
        ]
    )

# ---------- УРОВЕНЬ СЛОЖНОСТИ ----------

chat_levels: dict[int, str] = {}  # chat_id -> "easy"/"medium"/"hard"

@dp.message(Command("choose_level"))
async def choose_level(msg: types.Message):
    if msg.chat.type == "private":
        await msg.answer("Выбор уровня доступен только в группах.")
        return
    await msg.answer("Выберите уровень сложности для текущей игры:", reply_markup=kb_level_selection())

@dp.callback_query(lambda c: c.data.startswith("level_"))
async def set_level_callback(call: types.CallbackQuery):
    level = call.data.split("_")[1]  # easy / medium / hard
    chat_levels[call.message.chat.id] = level
    await call.answer(f"✅ Уровень сложности установлен: {level.capitalize()}")
    await call.message.edit_text(f"✅ Уровень сложности выбран: {level.capitalize()}")

# ---------- /start ----------

@dp.message(Command("start"))
async def start(msg: types.Message):
    if msg.chat.type == "private":
        await msg.answer(
            "Привет!\n\n"
            "Этот бот создан IT-командой Interact Club of Bishkek "
            "для проведения командных игр.\n\n"
            "Добавьте бота в группу и дайте ему права администратора."
        )
    else:
        await msg.answer("Бот готов! Используйте /choose_level чтобы выбрать уровень игры или /start_crocodile чтобы начать.")

# ---------- /start_crocodile ----------

@dp.message(Command("start_crocodile"))
async def start_game(msg: types.Message):
    if msg.chat.type == "private":
        await msg.answer("Игра доступна только в группах.")
        return

    # manager.load_words_if_needed()  <-- удаляем эту строку

    level = chat_levels.get(msg.chat.id, "easy")  # если не выбран, по умолчанию лёгкий
    word = manager.get_random_word(level)

    await manager.start_round(
        chat_id=msg.chat.id,
        leader_id=msg.from_user.id,
        leader_name=msg.from_user.username or msg.from_user.first_name
    )

    await msg.answer(
        f"🎭 @{msg.from_user.username or msg.from_user.first_name} объясняет слово!",
        reply_markup=kb_start()
    )


# ---------- ПРОВЕРКА УГАДЫВАНИЙ ----------

@dp.message(
    F.chat.type.in_({"group", "supergroup"}) &
    F.text &
    ~F.text.startswith("/")
)
async def check_guess(msg: types.Message):
    result = await manager.register_guess(
        chat_id=msg.chat.id,
        user_id=msg.from_user.id,
        username=msg.from_user.username or msg.from_user.first_name,
        text=msg.text
    )

    if result:
        await msg.answer(
            f"🎉 @{result['username']} угадал слово: {result['word']}",
            reply_markup=kb_leader()
        )

# ---------- /stats ----------

@dp.message(Command("stats"))
async def stats(msg: types.Message):
    if msg.chat.type == "private":
        await msg.answer("Статистика доступна только в группах.")
        return

    if not manager.stats:
        await msg.answer("Статистика пока пуста.")
        return

    lines = ["🏆 **Статистика игроков:**\n"]
    for user_id, stat in manager.stats.items():
        display_name = stat.get("name", "Игрок")
        led = stat.get("led", 0)
        guessed = stat.get("guessed", 0)
        failed = stat.get("failed", 0)

        lines.append(
            f"👤 [{display_name}](tg://user?id={user_id})\n"
            f"   🎭 Ведущий: {led}\n"
            f"   ✅ Угадал: {guessed}\n"
            f"   💀 Проиграл: {failed}\n"
        )

    await msg.answer("\n".join(lines), parse_mode="Markdown")

# ---------- CALLBACKS ----------

@dp.callback_query()
async def callbacks(call: types.CallbackQuery):
    session = manager.chats.get(call.message.chat.id)
    if not session:
        await call.answer("Раунд не активен", show_alert=True)
        return

    user = call.from_user
    data = call.data

    if data in ("view_word", "change_word") and user.id != session["leader_id"]:
        await call.answer("Вы не ведущий.", show_alert=True)
        return

    if data == "view_word":
        await call.answer(f"📝 Ваше слово:\n{session['word']}", show_alert=True)
        return

    if data == "change_word":
        new_word = await manager.change_word(call.message.chat.id)
        await call.answer(f"🔄 Новое слово:\n{new_word}", show_alert=True)
        return

    if data == "want_leader":
        new_word = await manager.ask_to_be_leader(
            call.message.chat.id,
            user.id,
            user.username or user.first_name
        )
        await call.message.answer(
            f"⭐ @{user.username or user.first_name} теперь ведущий!",
            reply_markup=kb_start()
        )
        await call.answer(f"📝 Ваше слово:\n{new_word}", show_alert=True)

# ---------- ЗАПУСК ----------

async def main():
    print("[INFO] Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
