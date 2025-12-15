import random
from collections import Counter

MAFIA_TEAM = ["mafia", "don"]
CIVILIAN_TEAM = ["civilian", "doctor", "sheriff"]

ROLE_NAMES = {
    "mafia": "Мафия",
    "don": "Дон",
    "doctor": "Доктор",
    "sheriff": "Шериф",
    "civilian": "Мирный житель"
}

class MafiaGame:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.players = {}
        self.phase = "lobby" 
        self.lobby_open = True
        self.lobby_message_id = None
        self.night_messages = [] 
        
        # Для мгновенного старта
        self.creator_id = None 

        # Действия ночью/днем
        self.mafia_votes = {}
        self.vote_votes = {}
        self.doctor_target = None
        self.sheriff_target = None
        self.sheriff_action_type = None 
        
        # Настройки по умолчанию
        self.settings = {
            "lobby_time": 60,
            "night_time": 30,
            "vote_time": 45,
            "min_players": 4 
        }

    def add_player(self, user_id, full_name):
        self.players[str(user_id)] = {
            "name": full_name,
            "role": None,
            "alive": True,
            "last_word_allowed": False # НОВОЕ: Для последнего слова
        }

    def alive(self) -> dict:
        """Возвращает словарь только живых игроков."""
        return {uid: p for uid, p in self.players.items() if p["alive"]}

    def assign_roles(self):
        player_count = len(self.players)
        
        # Определение количества ролей
        num_mafia = max(1, player_count // 4)
        num_don = 1 if num_mafia >= 2 else 0 # 1 Дон, если всего мафии >= 2
        num_mafia_basic = num_mafia - num_don
        
        num_sheriff = 1
        num_doctor = 1
        
        required_special = num_mafia + num_sheriff + num_doctor
        num_civilians = max(0, player_count - required_special)
        
        roles = []
        roles.extend(["don"] * num_don)
        roles.extend(["mafia"] * num_mafia_basic)
        roles.extend(["sheriff"] * num_sheriff)
        roles.extend(["doctor"] * num_doctor)
        roles.extend(["civilian"] * num_civilians)

        # Если количество ролей не совпало из-за округления, балансируем мирными
        while len(roles) < player_count:
             roles.append("civilian")
        while len(roles) > player_count:
             roles.pop() # Удаляем лишнюю мирную роль

        random.shuffle(roles)

        # Присвоение ролей игрокам
        player_ids = list(self.players.keys())
        for i, uid in enumerate(player_ids):
            self.players[uid]["role"] = roles[i]