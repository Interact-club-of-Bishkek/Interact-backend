# mafia/stats.py
import json

PLAYER_STATS = {}
STATS_FILE = "stats_data.json"

def load_stats():
    global PLAYER_STATS
    try:
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            PLAYER_STATS = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        PLAYER_STATS = {}

def save_stats():
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(PLAYER_STATS, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка сохранения статистики: {e}")

def inc(uid: str, key: str, value: int = 1):
    if uid not in PLAYER_STATS:
        PLAYER_STATS[uid] = {"games": 0, "wins": 0}
    PLAYER_STATS[uid][key] = PLAYER_STATS[uid].get(key, 0) + value
    # В реальном проекте: вызывать save_stats периодически, а не на каждое изменение.