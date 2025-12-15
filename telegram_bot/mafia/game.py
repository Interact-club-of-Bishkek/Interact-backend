import json
import random
from pathlib import Path

MAFIA_TEAM = ["mafia", "don"]

class MafiaGame:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.players = {}
        self.phase = "lobby"
        self.lobby_open = True
        
        # ИЗМЕНЕНИЕ: Храним ID сообщения, а не сам объект сообщения
        self.lobby_message_id = None 
        # Объект бота нужен будет для отправки, но хранить его тут нельзя
        self.bot = None 

        self.mafia_votes = {}
        self.vote_votes = {}
        self.settings = self.load_settings()

    def load_settings(self):
        # (Ваш код загрузки настроек без изменений)
        path = Path("settings.json")
        default = {"lobby_time": 60, "night_time": 30, "vote_time": 30, "min_players": 4, "roles": {"mafia": True}}
        if not path.exists(): return default
        try: return json.loads(path.read_text(encoding='utf-8'))
        except: return default

    def add_player(self, uid, name):
        # UID храним как строку для JSON совместимости
        self.players[str(uid)] = {"name": name, "role": None, "alive": True}

    def alive(self):
        return {u: p for u, p in self.players.items() if p["alive"]}

    def mafia(self):
        return {u: p for u, p in self.players.items() if p["alive"] and p["role"] in MAFIA_TEAM}

    def assign_roles(self):
        # (Ваш код раздачи ролей без изменений)
        # Убедитесь, что используете list(self.players.keys()) так как ключи могут быть str
        count = len(self.players)
        role_pool = ["mafia"]
        # ... логика добавления ролей ...
        while len(role_pool) < count: role_pool.append("civilian")
        random.shuffle(role_pool)
        for uid, role in zip(self.players.keys(), role_pool):
            self.players[uid]["role"] = role

    def check_winner(self):
        alive = self.alive().values()
        m = len([p for p in alive if p["role"] in MAFIA_TEAM])
        c = len([p for p in alive if p["role"] not in MAFIA_TEAM])
        if m == 0: return "civilian"
        if m >= c: return "mafia"
        return None