import random

MAFIA_ROLES = ["mafia", "don"]
CIVIL_ROLES = ["civilian", "doctor", "sheriff", "prostitute", "bodyguard"]

class MafiaGame:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.players = {}
        self.phase = "setup"  # setup -> lobby -> night -> day
        self.mafia_votes = {}
        self.vote_votes = {}
        self.settings = {
            "lobby_time": 60,
            "night_time": 45,
            "vote_time": 45,
            "min_players": 5,
            "roles": {
                "mafia": True,
                "don": True,
                "maniac": True,
                "doctor": True,
                "sheriff": True,
                "bodyguard": True,
                "prostitute": True,
                "kamikaze": True
            }
        }

    def add_player(self, uid, name):
        self.players[uid] = {"name": name, "role": None, "alive": True}

    def alive(self):
        return {u: p for u, p in self.players.items() if p["alive"]}

    def mafia(self):
        return {u: p for u, p in self.players.items() if p["alive"] and p["role"] in MAFIA_ROLES}

    def assign_roles(self):
        n = len(self.players)
        roles = []
        # базовые роли
        if self.settings["roles"]["doctor"]:
            roles.append("doctor")
        if self.settings["roles"]["sheriff"]:
            roles.append("sheriff")
        if self.settings["roles"]["mafia"]:
            roles.append("mafia")
        if n >= 6 and self.settings["roles"]["mafia"]:
            roles.append("mafia")
        if n >= 7 and self.settings["roles"]["don"]:
            roles.append("don")
        if n >= 8 and self.settings["roles"]["prostitute"]:
            roles.append("prostitute")
        if n >= 9 and self.settings["roles"]["bodyguard"]:
            roles.append("bodyguard")
        if n >= 10 and self.settings["roles"]["maniac"]:
            roles.append("maniac")
        if n >= 11 and self.settings["roles"]["kamikaze"]:
            roles.append("kamikaze")
        while len(roles) < n:
            roles.append("civilian")
        random.shuffle(roles)
        for uid, role in zip(self.players, roles):
            self.players[uid]["role"] = role

    def mafia_target(self):
        if len(self.mafia_votes) < len(self.mafia()):
            return None
        values = list(self.mafia_votes.values())
        return values[0] if all(v == values[0] for v in values) else None

    def check_winner(self):
        alive = self.alive().values()
        mafia = [p for p in alive if p["role"] in MAFIA_ROLES]
        maniac = [p for p in alive if p["role"] == "maniac"]
        civilians = [p for p in alive if p["role"] in CIVIL_ROLES]
        if maniac and len(alive) == 1:
            return "maniac"
        if not mafia and not maniac:
            return "civilians"
        if mafia and len(mafia) >= len(civilians) + len(maniac):
            return "mafia"
        return None
