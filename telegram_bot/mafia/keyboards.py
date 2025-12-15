from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def join_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Присоединиться", callback_data="join")
    return kb.as_markup()

def players_kb(players_dict: dict, action: str):
    """
    Генерирует кнопки со списком живых игроков.
    action: 'kill' или 'vote'
    """
    kb = InlineKeyboardBuilder()
    for uid, data in players_dict.items():
        # callback_data будет вида "kill:123456789"
        kb.button(text=data['name'], callback_data=f"{action}:{uid}")
    
    # Выстраиваем в 1 столбец (можно 2)
    kb.adjust(1)
    return kb.as_markup()