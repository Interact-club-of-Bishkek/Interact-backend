import os
import asyncio
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

from crocodile.crocodile_game import CrocodileManager

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(TOKEN)
dp = Dispatcher()
manager = CrocodileManager()
manager.bot = bot  # чтобы уведомления таймера могли отправлять сообщения

# --- Кнопки ---
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

# --- Команда /start ---
@dp.message(Command("start"))
async def start(msg: types.Message):
    if msg.chat.type == "private":
        await msg.answer(
            "Привет!\n\n"
            "Этот бот создан IT-командой Международной благотворительной Организации Interact Club of Bishkek "
            "для облегчения работы волонтеров и проведения веселых командных игр!\n\n"
            "Чтобы играть, добавьте бота в группу и дайте ему права администратора."
        )
    else:
        await msg.answer("Бот готов к игре! Используйте /start_crocodile чтобы начать раунд.")

# --- Команда /start_crocodile ---
@dp.message(Command("start_crocodile"))
async def start_game(msg: types.Message):
    if msg.chat.type == "private":
        await msg.answer("Чтобы играть, добавьте бота в группу и дайте ему права администратора.")
        return

    if not hasattr(manager, "words") or not manager.words:
        manager.load_words()

    word = await manager.start_round(
        chat_id=msg.chat.id,
        leader_id=msg.from_user.id,
        leader_name=msg.from_user.username or msg.from_user.first_name
    )

    await msg.answer(f"@{msg.from_user.username or msg.from_user.first_name} объясняет слово!", reply_markup=kb_start())

# --- Проверка угадываний ---
@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def check_guess(msg: types.Message):
    if not hasattr(manager, "words") or not manager.words:
        return  # если игра не запущена

    text = msg.text.strip().lower()
    res = await manager.register_guess(
        chat_id=msg.chat.id,
        user_id=msg.from_user.id,
        username=msg.from_user.username or msg.from_user.first_name,
        text=text
    )

    if res:
        await msg.answer(f"🎉 @{msg.from_user.username or msg.from_user.first_name} угадал слово: {res['word']}", reply_markup=kb_leader())

# --- Команда /stats ---
@dp.message(Command("stats"))
async def stats(msg: types.Message):
    if msg.chat.type == "private":
        await msg.answer("Статистика доступна только в группах.")
        return

    if not manager.stats:
        await msg.answer("Статистика пока пуста.")
        return

    lines = ["🏆 Статистика игроков:"]
    for user_id, stat in manager.stats.items():
        name = stat.get("name", f"ID {user_id}")
        lines.append(
            f"• {name}: Ведущий: {stat.get('led',0)}, Угадывал: {stat.get('guessed',0)}, Проигрыши: {stat.get('failed',0)}"
        )

    await msg.answer("\n".join(lines))

# --- Callbacks ---
@dp.callback_query()
async def cb(call: types.CallbackQuery):
    session = manager.chats.get(call.message.chat.id)
    if not session:
        return await call.answer("Нет раунда", show_alert=True)

    user = call.from_user
    data = call.data

    if data in ("view_word","change_word") and user.id != session["leader_id"]:
        return await call.answer("Сейчас не ваша очередь.", show_alert=True)

    if data == "view_word":
        return await call.answer(f"📝 Ваше слово:\n\n{session['word']}", show_alert=True)

    if data == "change_word":
        new_word = await manager.change_word(call.message.chat.id)
        return await call.answer(f"🔄 Новое слово:\n{new_word}", show_alert=True)

    if data == "want_leader":
        new_word = await manager.ask_to_be_leader(call.message.chat.id, user.id, user.username or user.first_name)
        await call.message.answer(f"⭐ @{user.username or user.first_name} теперь ведущий!", reply_markup=kb_start())
        return await call.answer(f"📝 Ваше слово:\n{new_word}", show_alert=True)

# --- Запуск ---
async def main():
    print("[INFO] Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
