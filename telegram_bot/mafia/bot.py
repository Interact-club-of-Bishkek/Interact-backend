# mafia/bot.py
import os
import asyncio
from aiogram import Bot, types, F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(TOKEN)
mafia_router = Router()

# ---------- Игра ----------
class MafiaGame:
    def __init__(self):
        self.players = {}  # user_id -> {"name": str, "alive": bool}
        self.settings = {
            "lobby_time": 60,
            "night_time": 30,
            "vote_time": 20,
            "min_players": 4,
            "roles": {"mafia": True, "doctor": True, "detective": True}
        }
        self.leader_id = None
        self.active = False

games: dict[int, MafiaGame] = {}  # chat_id -> MafiaGame

# ---------- InlineKeyboard ----------
def join_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton("➕ Войти в игру", callback_data="join")]]
    )

def settings_kb(game: MafiaGame) -> InlineKeyboardMarkup:
    buttons = []

    # Настройки времени и игроков
    buttons.append([
        InlineKeyboardButton(f"⏱ Лобби: {game.settings['lobby_time']} сек", callback_data="lobby_time"),
        InlineKeyboardButton(f"🌙 Ночь: {game.settings['night_time']} сек", callback_data="night_time")
    ])
    buttons.append([
        InlineKeyboardButton(f"🗳 Голосование: {game.settings['vote_time']} сек", callback_data="vote_time"),
        InlineKeyboardButton(f"👥 Мин. игроков: {game.settings['min_players']}", callback_data="min_players")
    ])

    # Роли
    for role, enabled in game.settings["roles"].items():
        buttons.append([InlineKeyboardButton(f"{role.capitalize()} {'✅' if enabled else '❌'}", callback_data=f"role_{role}")])

    # Начать игру
    buttons.append([InlineKeyboardButton("✅ Начать игру", callback_data="start_game")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ---------- Helper ----------
async def safe_edit_reply_markup(message: types.Message, new_kb: InlineKeyboardMarkup):
    if message.reply_markup != new_kb:
        try:
            await message.edit_reply_markup(reply_markup=new_kb)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

# ---------- /start ----------
@mafia_router.message(Command("start"))
async def start(msg: types.Message):
    if msg.chat.type == "private":
        await msg.answer(
            "Привет!\n\n"
            "Этот бот создан IT-командой Interact Club of Bishkek "
            "для проведения командных игр.\n\n"
            "Добавьте бота в группу и дайте ему права администратора."
        )
    else:
        await msg.answer(
            "Бот готов! Используйте /start_mafia чтобы начать игру или /settings чтобы настроить игру."
        )

# ---------- /start_mafia ----------
@mafia_router.message(Command("start_mafia"))
async def start_mafia(msg: types.Message):
    if msg.chat.type == "private":
        await msg.answer("Игра доступна только в группах.")
        return

    chat_id = msg.chat.id
    if chat_id not in games:
        games[chat_id] = MafiaGame()

    game = games[chat_id]
    game.leader_id = msg.from_user.id
    game.active = True

    await msg.answer(
        f"🎮 Игра началась! @{msg.from_user.username or msg.from_user.first_name} теперь ведущий.\n"
        "Игроки могут присоединяться к игре:",
        reply_markup=join_kb()
    )

# ---------- Присоединение к игре ----------
@mafia_router.callback_query(lambda c: c.data == "join")
async def join_game(call: types.CallbackQuery):
    user = call.from_user
    chat_id = call.message.chat.id

    game = games.get(chat_id)
    if not game or not game.active:
        await call.answer("Игра не запущена.", show_alert=True)
        return

    if user.id in game.players:
        await call.answer("Вы уже в игре!", show_alert=True)
        return

    game.players[user.id] = {"name": user.full_name, "alive": True}
    await call.answer(f"Вы присоединились к игре, {user.full_name}!")

    # Обновляем кнопки безопасно
    await safe_edit_reply_markup(call.message, join_kb())

# ---------- /settings ----------
@mafia_router.message(Command("settings"))
async def settings(msg: types.Message):
    chat_id = msg.chat.id
    game = games.get(chat_id)
    if not game:
        await msg.answer("Игра пока не запущена.")
        return

    await msg.answer("🎮 Настройка игры:", reply_markup=settings_kb(game))

# ---------- CALLBACKS для настроек ----------
@mafia_router.callback_query()
async def settings_callbacks(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    game = games.get(chat_id)
    if not game:
        await call.answer("Игра не запущена.", show_alert=True)
        return

    data = call.data
    if data.startswith("role_"):
        role = data.split("_")[1]
        game.settings["roles"][role] = not game.settings["roles"][role]
        await safe_edit_reply_markup(call.message, settings_kb(game))
        await call.answer(f"{role.capitalize()} {'включена' if game.settings['roles'][role] else 'выключена'}")
    elif data in ("lobby_time", "night_time", "vote_time", "min_players"):
        # Можно добавить логику изменения числовых настроек
        await call.answer("Эта настройка пока не реализована.", show_alert=True)
    elif data == "start_game":
        await call.answer("Игра начинается!", show_alert=True)
        # Здесь можно добавить логику старта раунда

# ---------- /players ----------
@mafia_router.message(Command("players"))
async def show_players(msg: types.Message):
    chat_id = msg.chat.id
    game = games.get(chat_id)
    if not game:
        await msg.answer("Игра пока не запущена.")
        return

    if not game.players:
        await msg.answer("Игроки пока не присоединились.")
        return

    lines = [f"👥 Игроки ({len(game.players)}):"]
    for p in game.players.values():
        lines.append(f" - {p['name']} {'(в игре)' if p['alive'] else '(выбыл)'}")

    await msg.answer("\n".join(lines))

def register_mafia_handlers(dp, bot_instance):
    """Подключение всех обработчиков мафии к Dispatcher"""
    from mafia.bot import mafia_router  # убедимся, что импорт самого себя безопасен
    dp.include_router(mafia_router)