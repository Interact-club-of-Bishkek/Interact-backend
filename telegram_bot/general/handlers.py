from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter # <-- Добавлен импорт StateFilter
from aiogram.enums import ChatType
from typing import Optional

# ❗ ИМПОРТ КНОПКИ ИГРЫ КРОКОДИЛ
try:
    from crocodile.crocodile_runner import kb_play_croc 
except ImportError:
    # Заглушка, если реальный импорт недоступен
    def kb_play_croc():
        return types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🐊 Играть в Крокодила", callback_data="start_croc_game")]
        ])

general_router = Router()

# ---------- КНОПКИ ----------

def club_keyboard() -> types.InlineKeyboardMarkup:
    """Генерирует кнопки, специфичные для Interact Club (для ЛС)."""
    buttons = [
        [
            types.InlineKeyboardButton(
                text="🌟 Оставить заявку стать волонтером", 
                callback_data="volunteer_apply" # <-- Колбэк, который должен быть обработан FSM
            )
        ],
        [
            types.InlineKeyboardButton(
                text="🧠 ИИ Ассистент Interact Club", 
                callback_data="ai_assistant"
            )
        ],
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)


def game_keyboard() -> types.InlineKeyboardMarkup:
    """Генерирует кнопки для игр (для групп)."""
    
    # 1. Кнопка Крокодил
    croc_button: types.InlineKeyboardButton = kb_play_croc().inline_keyboard[0][0]

    # 2. Условная Кнопка Мафия
    mafia_button = types.InlineKeyboardButton(
        text="🔫 Играть в Мафию", 
        callback_data="start_mafia_game" 
    )
    
    buttons = [
        [croc_button],
        [mafia_button],
    ]
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------- ТЕКСТЫ ----------

def get_welcome_text(user_name: Optional[str]) -> str:
    """Формирует приветственный текст для ЛС."""
    # Используем HTML-теги для форматирования, чтобы соответствовать остальному коду
    user_greeting = f"✨ <b>Добро пожаловать, {user_name}!</b> ✨\n\n" if user_name else "✨ <b>Добро пожаловать в Interact Club of Bishkek!</b> ✨\n\n"
    
    return (
        f"{user_greeting}"
        "Мы — международная благотворительная организация, объединяющая активную "
        "молодежь Бишкека для реализации социальных проектов и создания позитивных перемен.\n\n"
        "🤝 <b>Наша миссия:</b> Развивать лидерские качества, помогать обществу и строить дружеские связи.\n\n"
        "Выберите действие, чтобы узнать больше или начать свой путь с нами:"
    )

def get_group_start_text() -> str:
    """Формирует текст для группового чата при запуске игры."""
    return (
        "🎮 <b>Начнём игру!</b>\n"
        "Выберите игру, которую хотите запустить в этом чате.\n\n"
        "⚠️ Если вы ищете информацию о клубе, пожалуйста, используйте /start в личных сообщениях."
    )


# ---------- ХЕНДЛЕРЫ КОМАНД ----------

@general_router.message(Command("start"), F.chat.type == ChatType.PRIVATE, StateFilter(None)) # <-- Добавлен StateFilter(None)
async def handle_private_start(msg: types.Message):
    """Обрабатывает команду /start в личных сообщениях, только когда FSM неактивен."""
    user_name = msg.from_user.first_name if msg.from_user else "друг"
    welcome_text = get_welcome_text(user_name)
    
    await msg.answer(
        welcome_text,
        reply_markup=club_keyboard(), 
        parse_mode="HTML" # <-- Изменено на HTML
    )

@general_router.message(Command("start"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def handle_group_start(msg: types.Message):
    """Обрабатывает команду /start в групповых чатах (Кнопки игр)."""
    await msg.answer(
        get_group_start_text(),
        reply_markup=game_keyboard(), 
        parse_mode="HTML" # <-- Изменено на HTML
    )


# ---------- ХЕНДЛЕРЫ CALLBACKS ----------

@general_router.callback_query(F.data == "ai_assistant") 
async def handle_under_development(call: types.CallbackQuery):
    """Обрабатывает нажатие кнопки "ИИ Ассистент Interact Club"."""
    await call.answer("🛠 Функция находится в разработке. Скоро вернемся с обновлениями!", show_alert=True)