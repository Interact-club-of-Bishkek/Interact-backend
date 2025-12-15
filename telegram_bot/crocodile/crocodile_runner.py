# crocodile/bot_handlers.py
import os
from aiogram import types, F, Router, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pathlib import Path

# Импортируем менеджер (но не создаем бота здесь!)
from crocodile.crocodile_game import CrocodileManager

# Создаем роутер
crocodile_router = Router()

# Создаем менеджер игры.
# ВАЖНО: Мы пока не присваиваем ему bot, сделаем это в main.py
manager = CrocodileManager()

BASE_DIR = Path(__file__).resolve().parent

# ---------- КНОПКИ (Без изменений) ----------
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
chat_levels: dict[int, str] = {}

@crocodile_router.message(Command("choose_level"))
async def choose_level(msg: types.Message):
    if msg.chat.type == "private":
        await msg.answer("Выбор уровня доступен только в группах.")
        return
    await msg.answer("Выберите уровень сложности для текущей игры:", reply_markup=kb_level_selection())

@crocodile_router.callback_query(F.data.startswith("level_"))
async def set_level_callback(call: types.CallbackQuery):
    level = call.data.split("_")[1]
    chat_levels[call.message.chat.id] = level
    await call.answer(f"✅ Уровень сложности установлен: {level.capitalize()}")
    await call.message.edit_text(f"✅ Уровень сложности выбран: {level.capitalize()}")

# ---------- /start_crocodile ----------
@crocodile_router.message(Command("start_crocodile"))
async def start_game(msg: types.Message, bot: Bot): # bot прилетит автоматически
    if msg.chat.type == "private":
        await msg.answer("Игра доступна только в группах.")
        return
    
    # На всякий случай обновляем бота в менеджере, чтобы таймеры работали
    if manager.bot is None:
        manager.bot = bot

    level = chat_levels.get(msg.chat.id, "easy")
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
# ВАЖНОЕ ИСПРАВЛЕНИЕ:
# Добавляем фильтр: срабатывать ТОЛЬКО если в этом чате идет игра.
# Иначе этот хендлер будет воровать сообщения у Мафии.

def is_game_active(msg: types.Message) -> bool:
    # Проверяем, есть ли этот чат в активных играх менеджера
    return msg.chat.id in manager.chats

@crocodile_router.message(
    F.chat.type.in_({"group", "supergroup"}),
    F.text,
    ~F.text.startswith("/"),
    is_game_active  # <--- Вот этот фильтр спасает ситуацию
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
@crocodile_router.message(Command("stats"))
async def stats(msg: types.Message):
    if msg.chat.type == "private": return

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
            f"👤 {display_name}\n" # Убрал markdown ссылку, часто вызывает ошибки парсинга если нет username
            f"   🎭 Ведущий: {led}\n"
            f"   ✅ Угадал: {guessed}\n"
            f"   💀 Проиграл: {failed}\n"
        )

    await msg.answer("\n".join(lines), parse_mode="Markdown")

# ---------- CALLBACKS (Общий обработчик) ----------
@crocodile_router.callback_query(F.data.in_({"view_word", "change_word", "want_leader"}))
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