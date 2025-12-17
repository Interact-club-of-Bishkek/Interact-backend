import html
from aiogram import types, F, Router, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from crocodile.crocodile_game import CrocodileManager

# Создаем роутер
crocodile_router = Router()

# Создаем менеджер игры
manager = CrocodileManager()

# ---------- КНОПКИ ----------

def kb_play_croc() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🐊 Играть в Крокодила", callback_data="start_croc_game")]
        ]
    )

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
    level_rus = {"easy": "Лёгкий", "medium": "Средний", "hard": "Тяжёлый"}.get(level, level)
    
    await call.answer(f"✅ Уровень сложности установлен: {level_rus}")
    await call.message.edit_text(f"✅ Уровень сложности выбран: {level_rus}")

# ---------- СТАРТ ИГРЫ ----------

async def start_game_logic(chat_id: int, user: types.User, bot: Bot):
    # Обновляем бота в менеджере
    if manager.bot is None:
        manager.bot = bot

    level = chat_levels.get(chat_id, "easy")
    
    # Запускаем раунд
    await manager.start_round(
        chat_id=chat_id,
        leader_id=user.id,
        leader_name=user.username or user.first_name,
        level=level
    )
    
    # Экранируем имя пользователя для HTML
    safe_name = html.escape(user.first_name)
    
    await bot.send_message(
        chat_id,
        f"🎭 <b>{safe_name}</b> объясняет слово!",
        reply_markup=kb_start(),
        parse_mode="HTML"
    )

@crocodile_router.message(Command("start_crocodile"))
async def start_game_command(msg: types.Message, bot: Bot):
    if msg.chat.type == "private":
        await msg.answer("Игра доступна только в группах.")
        return
    await start_game_logic(msg.chat.id, msg.from_user, bot)

@crocodile_router.callback_query(F.data == "start_croc_game")
async def start_game_callback(call: types.CallbackQuery, bot: Bot):
    await call.answer() 
    if call.message.chat.type == "private":
        await call.message.answer("Игра доступна только в группах.")
        return
    await start_game_logic(call.message.chat.id, call.from_user, bot)

# ---------- ПРОВЕРКА УГАДЫВАНИЙ ----------

def is_game_active(msg: types.Message) -> bool:
    return msg.chat.id in manager.chats

@crocodile_router.message(
    F.chat.type.in_({"group", "supergroup"}),
    F.text,
    ~F.text.startswith("/"),
    is_game_active 
)
async def check_guess(msg: types.Message):
    result = await manager.register_guess(
        chat_id=msg.chat.id,
        user_id=msg.from_user.id,
        username=msg.from_user.username or msg.from_user.first_name,
        text=msg.text
    )

    if result:
        # Экранируем данные для безопасности HTML
        winner_name = html.escape(result['username'])
        guessed_word = html.escape(result['word'])

        await msg.answer(
            f"🎉 <b>{winner_name}</b> угадал слово: <b>{guessed_word}</b>",
            reply_markup=kb_leader(),
            parse_mode="HTML" # Используем HTML вместо Markdown
        )

# ---------- /stats (СТАТИСТИКА ТЕКУЩЕГО ЧАТА) ----------

@crocodile_router.message(Command("stats"))
async def stats(msg: types.Message):
    if msg.chat.type == "private": 
        return

    # Берем статистику ТОЛЬКО для текущего чата по chat_id
    chat_stats = manager.stats.get(str(msg.chat.id))

    if not chat_stats:
        await msg.answer("📊 В этом чате статистика пока пуста. Сыграйте в крокодила!")
        return

    lines = ["🏆 <b>Статистика игроков этого чата:</b>\n"]
    
    # Сортировка: у кого больше угаданных
    sorted_stats = sorted(chat_stats.items(), key=lambda item: item[1].get("guessed", 0), reverse=True)
    
    # Ограничим вывод топ-15, чтобы сообщение не было огромным
    for user_id, stat in sorted_stats[:15]:
        display_name = html.escape(stat.get("name", "Игрок"))
        led = stat.get("led", 0)
        guessed = stat.get("guessed", 0)
        failed = stat.get("failed", 0)

        lines.append(
            f"👤 <b>{display_name}</b>\n" 
            f"   🎭 Ведущий: {led} | ✅ Угадал: {guessed} | 💀 Проиграл: {failed}\n"
        )

    await msg.answer("\n".join(lines), parse_mode="HTML")

# ---------- CALLBACKS ----------

@crocodile_router.callback_query(F.data.in_({"view_word", "change_word", "want_leader"}))
async def callbacks(call: types.CallbackQuery, bot: Bot):
    session = manager.chats.get(call.message.chat.id)
    
    # Логика "Хочу быть ведущим", если игра закончилась, но висит кнопка
    if call.data == "want_leader" and not session:
         user = call.from_user
         new_word = await manager.ask_to_be_leader(
            call.message.chat.id,
            user.id,
            user.username or user.first_name
         )
         # Пытаемся убрать кнопки у старого сообщения
         try: await call.message.edit_reply_markup(reply_markup=None)
         except: pass

         safe_name = html.escape(user.username or user.first_name)
         await call.message.answer(
            f"⭐ <b>{safe_name}</b> теперь ведущий!",
            reply_markup=kb_start(),
            parse_mode="HTML"
         )
         await call.answer(f"📝 Ваше слово:\n{new_word}", show_alert=True)
         return

    if not session:
        await call.answer("Раунд не активен", show_alert=True)
        return

    user = call.from_user
    data = call.data

    # Только ведущий может смотреть/менять слово
    if data in ("view_word", "change_word") and user.id != session["leader_id"]:
        await call.answer("Вы не ведущий.", show_alert=True)
        return

    if data == "view_word":
        await call.answer(f"📝 Ваше слово:\n{session['word']}", show_alert=True)
        return

    if data == "change_word":
        new_word = await manager.change_word(call.message.chat.id)
        if new_word:
            await call.answer(f"🔄 Новое слово:\n{new_word}", show_alert=True)
        else:
            await call.answer("Ошибка: не удалось найти новое слово.", show_alert=True)
        return

    if data == "want_leader":
        # Перехват ведущего во время игры
        new_word = await manager.ask_to_be_leader(
            call.message.chat.id,
            user.id,
            user.username or user.first_name
        )
        try: await call.message.edit_reply_markup(reply_markup=None)
        except: pass

        safe_name = html.escape(user.username or user.first_name)
        await call.message.answer(
            f"⭐ <b>{safe_name}</b> теперь ведущий!",
            reply_markup=kb_start(),
            parse_mode="HTML"
        )
        await call.answer(f"📝 Ваше слово:\n{new_word}", show_alert=True)