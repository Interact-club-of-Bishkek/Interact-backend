import json
import os
from mafia.game import MafiaGame

DB_FILE = "mafia_db.json"

def _load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def _save_db(db):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def save_game(game: MafiaGame):
    db = _load_db()
    db[str(game.chat_id)] = {
        "chat_id": game.chat_id,
        "phase": game.phase,
        "lobby_open": game.lobby_open,
        "lobby_message_id": game.lobby_message_id,
        "night_messages": game.night_messages,
        "players": game.players,
        "mafia_votes": game.mafia_votes,
        "vote_votes": game.vote_votes,
        "doctor_target": game.doctor_target,
        "sheriff_target": game.sheriff_target,
        "sheriff_action_type": game.sheriff_action_type, 
        "settings": game.settings,
        "creator_id": game.creator_id
    }
    _save_db(db)

def load_game(chat_id: int):
    db = _load_db()
    g = db.get(str(chat_id))
    if not g:
        return None

    game = MafiaGame(chat_id)
    game.phase = g.get("phase", "lobby")
    game.lobby_open = g.get("lobby_open", True)
    game.lobby_message_id = g.get("lobby_message_id")
    game.night_messages = g.get("night_messages", [])
    game.players = g.get("players", {})
    game.mafia_votes = g.get("mafia_votes", {})
    game.vote_votes = g.get("vote_votes", {})
    game.doctor_target = g.get("doctor_target")
    game.sheriff_target = g.get("sheriff_target")
    game.sheriff_action_type = g.get("sheriff_action_type")
    game.settings = g.get("settings", game.settings)
    game.creator_id = g.get("creator_id")
    
    # Убедимся, что у всех игроков есть флаг last_word_allowed (для совместимости)
    for uid in game.players:
        if 'last_word_allowed' not in game.players[uid]:
             game.players[uid]['last_word_allowed'] = False

    return game

def delete_game(chat_id: int):
    db = _load_db()
    if str(chat_id) in db:
        del db[str(chat_id)]
        _save_db(db)

def get_all_games():
    db = _load_db()
    games = {}
    for chat_id, data in db.items():
        # Используем load_game для корректной десериализации
        game = load_game(int(chat_id))
        if game:
            games[int(chat_id)] = game
    return games