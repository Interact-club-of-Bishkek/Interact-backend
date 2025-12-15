import json
from pathlib import Path

FILE = Path("stats.json")

def load():
    if not FILE.exists():
        return {}
    try:
        return json.loads(FILE.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return {}

def save(data):
    FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

def inc(user_id, field):
    if field not in ("games", "wins", "deaths"):
        raise ValueError(f"Недопустимое поле: {field}")

    data = load()
    # Ключ должен быть строкой для JSON
    uid = str(user_id)
    user = data.setdefault(uid, {"games": 0, "wins": 0, "deaths": 0})
    user[field] += 1
    save(data)