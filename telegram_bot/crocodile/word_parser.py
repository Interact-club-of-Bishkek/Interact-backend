import random
import json
import os

CACHE_FILE = "filtered_words.json"

def preprocess_words(file_path: str, limit: int = 2000) -> list[str]:
    """
    Загружает слова из файла, фильтрует по уникальности и кеширует результат.
    Если кеш есть, подгружает из него.
    """
    # Загружаем из кеша, если есть
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                words = json.load(f)
                print(f"[INFO] Загружено {len(words)} слов из кеша")
                return words
        except Exception as e:
            print(f"[WARNING] Не удалось загрузить кеш: {e}")

    # Загружаем слова из файла
    words = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip().lower()
                if w.isalpha() and len(w) > 2:
                    words.append(w)
    except Exception as e:
        print(f"[ERROR] Загрузка файла: {e}")
        return ["слово", "дом", "кот"]

    # Фильтруем уникальные слова
    seen = set()
    filtered = []
    for w in words:
        if w not in seen:
            filtered.append(w)
            seen.add(w)

    random.shuffle(filtered)
    filtered = filtered[:limit]

    # Сохраняем кеш
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False)
            print(f"[INFO] Словарь сохранен в {CACHE_FILE}")
    except Exception as e:
        print(f"[WARNING] Не удалось сохранить кеш: {e}")

    return filtered
