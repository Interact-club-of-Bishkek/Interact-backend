import json
import os
from pathlib import Path
from mafia.game import MafiaGame

DB_FILE = Path("active_games.json")

def _load_db():
    if not DB_FILE.exists():
        return {}
    try:
        return json.loads(DB_FILE.read_text(encoding='utf-8'))
    except:
        return {}

def _save_db(data):
    DB_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

def save_game(game: MafiaGame):
    data = _load_db()
    
    # Превращаем объект игры в словарь
    game_data = {
        "chat_id": game.chat_id,
        "phase": game.phase,
        "lobby_open": game.lobby_open,
        "lobby_message_id": game.lobby_message_id, # Важно сохранить ID сообщения
        "players": game.players,
        "mafia_votes": game.mafia_votes,
        "vote_votes": game.vote_votes,
        # Сохраняем настройки, если они менялись
        "settings": game.settings 
    }
    
    data[str(game.chat_id)] = game_data
    _save_db(data)

def load_game(chat_id: int) -> MafiaGame | None:
    data = _load_db()
    game_data = data.get(str(chat_id))
    
    if not game_data:
        return None
        
    # Восстанавливаем объект игры
    game = MafiaGame(chat_id)
    game.phase = game_data.get("phase", "lobby")
    game.lobby_open = game_data.get("lobby_open", True)
    game.lobby_message_id = game_data.get("lobby_message_id")
    game.players = game_data.get("players", {})
    game.mafia_votes = game_data.get("mafia_votes", {})
    game.vote_votes = game_data.get("vote_votes", {})
    game.settings = game_data.get("settings", game.settings)
    
    return game

def delete_game(chat_id: int):
    data = _load_db()
    if str(chat_id) in data:
        del data[str(chat_id)]
        _save_db(data)