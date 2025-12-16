from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Кнопка для лобби (Добавлена кнопка "Начать сейчас")
def join_kb(is_creator: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Присоединиться", callback_data="join")
    
    if is_creator:
        kb.button(text="🚀 Начать сейчас", callback_data="start_now")
        kb.adjust(1, 1) # Размещаем их отдельно
    else:
        kb.adjust(1)
        
    return kb.as_markup()

# Кнопка настроек
def settings_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    
    # Лобби
    kb.row(
        InlineKeyboardButton(text="⏱ Лобби -10с", callback_data="set_lobby_minus"),
        InlineKeyboardButton(text="⏱ Лобби +10с", callback_data="set_lobby_plus")
    )
    # Ночь
    kb.row(
        InlineKeyboardButton(text="🌙 Ночь -5с", callback_data="set_night_minus"),
        InlineKeyboardButton(text="🌙 Ночь +5с", callback_data="set_night_plus")
    )
    # Голосование
    kb.row(
        InlineKeyboardButton(text="🗳 Гол. -5с", callback_data="set_vote_minus"),
        InlineKeyboardButton(text="🗳 Гол. +5с", callback_data="set_vote_plus")
    )
    # Мин. игроков
    kb.row(
        InlineKeyboardButton(text="👥 Мин. -1", callback_data="set_min_minus"),
        InlineKeyboardButton(text="👥 Мин. +1", callback_data="set_min_plus")
    )
    
    return kb.as_markup()

# Клавиатура для выбора игрока (убийство, лечение, голосование)
def players_kb(players: dict, chat_id: int, exclude: str = None, action: str = "vote") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    
    for uid, p in players.items():
        if uid != exclude:
            kb.button(text=p["name"], callback_data=f"{action}:{chat_id}:{uid}")
    
    kb.adjust(2, repeat=True)
    return kb.as_markup()

# Выбор действия шерифа
def sheriff_choice_kb(chat_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    
    kb.button(text="🕵️ Проверить", callback_data=f"sh_choice:check:{chat_id}")
    kb.button(text="🔫 Застрелить", callback_data=f"sh_choice:kill:{chat_id}")
    
    kb.adjust(1)
    return kb.as_markup()

# --- ДОБАВЛЕНО ---
def games_menu_kb() -> InlineKeyboardMarkup:
    """Клавиатура с выбором игр по команде /start в группе."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Начать Мафию 🐺", callback_data="start_mafia_from_menu")
    builder.adjust(1)
    return builder.as_markup()
# -----------------