import json
from pathlib import Path

FILE = Path("stats.json")

def load():
    if not FILE.exists():
        return {}
    return json.loads(FILE.read_text())

def save(data):
    FILE.write_text(json.dumps(data, indent=2))

def inc(user_id, field):
    data = load()
    user = data.setdefault(str(user_id), {"games": 0, "wins": 0, "deaths": 0})
    user[field] += 1
    save(data)
