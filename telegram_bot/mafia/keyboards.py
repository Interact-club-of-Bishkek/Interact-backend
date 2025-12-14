# mafia/keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------- КНОПКИ ----------
def join_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Войти в игру", callback_data="join")]
        ]
    )


def players_kb(players: dict, action: str) -> InlineKeyboardMarkup:
    """
    Кнопки с игроками для выбора действия (например, для ночи или голосования)
    players: {user_id: {"name": str, "alive": bool}}
    action: str, callback action prefix
    """
    buttons = [
        [InlineKeyboardButton(text=f"👤 {p['name']}", callback_data=f"{action}:{uid}")]
        for uid, p in players.items() if p["alive"]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def settings_kb(game) -> InlineKeyboardMarkup:
    """
    Клавиатура настроек игры
    game.settings = {
        "lobby_time": int,
        "night_time": int,
        "vote_time": int,
        "min_players": int,
        "roles": {"mafia": True, "doctor": False, ...}
    }
    """
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⏱ Лобби: {game.settings['lobby_time']} сек",
                    callback_data="lobby_time"
                ),
                InlineKeyboardButton(
                    text=f"🌙 Ночь: {game.settings['night_time']} сек",
                    callback_data="night_time"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🗳 Голосование: {game.settings['vote_time']} сек",
                    callback_data="vote_time"
                ),
                InlineKeyboardButton(
                    text=f"👥 Мин. игроков: {game.settings['min_players']}",
                    callback_data="min_players"
                )
            ]
        ]
    )

    # Добавляем кнопки с ролями
    for role, enabled in game.settings.get("roles", {}).items():
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{role.capitalize()} {'✅' if enabled else '❌'}",
                callback_data=f"role_{role}"
            )
        ])

    # Кнопка "Начать игру"
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="✅ Начать игру", callback_data="start_game")
    ])

    return kb
    