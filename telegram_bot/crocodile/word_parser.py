import random
import json
from pymystem3 import Mystem
import chardet

M = Mystem()
CACHE_FILE = "filtered_words.json"

def preprocess_words(file_path: str, limit: int = 2000) -> list[str]:
    """
    Загружает слова из файла, фильтрует по лемме и кеширует результат.
    Если кеш есть, подгружает из него.
    """
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            words = json.load(f)
            print(f"[INFO] Загружено {len(words)} слов из кеша")
            return words
    except FileNotFoundError:
        pass

    words = []
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
            enc = chardet.detect(raw)['encoding'] or 'utf-8'
            text = raw.decode(enc, errors='ignore')

        for line in text.splitlines():
            w = line.strip().lower()
            if w.isalpha() and len(w) > 2:
                words.append(w)
    except Exception as e:
        print("[ERROR] Загрузка файла:", e)
        return ["слово", "дом", "кот"]

    seen_lemmas = set()
    filtered = []
    for w in words:
        try:
            lemma = M.lemmatize(w)[0].strip()
            if lemma and lemma not in seen_lemmas:
                filtered.append(w)
                seen_lemmas.add(lemma)
        except Exception:
            continue

    random.shuffle(filtered)
    filtered = filtered[:limit]

    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False)
            print(f"[INFO] Словарь сохранен в {CACHE_FILE}")
    except:
        pass

    return filtered
