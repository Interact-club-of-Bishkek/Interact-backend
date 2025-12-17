import random
import asyncio
import json
from pathlib import Path
from typing import Dict, Optional, List, Any

# ---------- PATHS ----------
BASE_DIR = Path(__file__).resolve().parent
STATS_FILE = BASE_DIR / "crocodile_stats.json"
CACHE_DIR = BASE_DIR / "cache_words"
CACHE_DIR.mkdir(exist_ok=True)

# ---------- УРОВНИ ----------
LEVELS = {
    "easy": ["nouns"],
    "medium": ["nouns", "adjectives"],
    "hard": ["nouns", "adjectives", "verbs"]
}

# ---------- КОЛОДЫ СЛОВ ----------
class WordDeck:
    def __init__(self, all_words: List[str]):
        self._all_words = all_words
        self._deck = list(all_words)
        random.shuffle(self._deck)

    def get_word(self) -> str:
        if not self._deck:
            self._deck = list(self._all_words)
            random.shuffle(self._deck)
            if not self._deck:
                 raise RuntimeError("Словарь пуст, не могу пополнить колоду.")
            print("[INFO] Колода слов пополнена и перемешана.")
            
        return self._deck.pop()

class CrocodileManager:
    def __init__(self):
        self.chats: Dict[int, dict] = {}
        # СТРУКТУРА: { "chat_id_str": { "user_id_str": { stats... } } }
        self.stats: Dict[str, Dict[str, Any]] = {} 
        self.words_decks: Dict[str, WordDeck] = {} 
        self.bot = None
        self.DEFAULT_DURATION = 300 # 5 минут

        self._load_stats()
        self._load_words_from_cache()

    # ==========================================================
    #                       СТАТИСТИКА
    # ==========================================================

    def _load_stats(self):
        if STATS_FILE.exists():
            try:
                with open(STATS_FILE, "r", encoding="utf-8") as f:
                    self.stats = json.load(f)
            except json.JSONDecodeError:
                self.stats = {}
        else:
            self.stats = {}

    def _save_stats(self):
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                self.stats,
                f,
                ensure_ascii=False,
                indent=2
            )

    def _ensure_user(self, chat_id: int, user_id: int, name: Optional[str] = None):
        """Проверяет наличие записи пользователя ВНУТРИ конкретного чата."""
        c_key = str(chat_id)
        u_key = str(user_id)

        # Если чата нет в статистике, создаем
        if c_key not in self.stats:
            self.stats[c_key] = {}

        # Если юзера нет в этом чате, создаем
        if u_key not in self.stats[c_key]:
            self.stats[c_key][u_key] = {
                "name": name or f"ID {user_id}",
                "led": 0,
                "guessed": 0,
                "failed": 0
            }
        elif name:
            # Обновляем имя, если оно изменилось
            self.stats[c_key][u_key]["name"] = name

    # ==========================================================
    #                           СЛОВА
    # ==========================================================

    def _load_words_from_cache(self):
        raw_words_by_level: Dict[str, List[str]] = {}

        for level, categories in LEVELS.items():
            combined: list[str] = []

            for cat in categories:
                file_path = CACHE_DIR / cat / "summary.json"
                if not file_path.exists():
                    continue
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        combined.extend(
                            w.lower()
                            for w in data
                            if isinstance(w, str) and w.isalpha() and len(w) > 2
                        )
                except Exception as e:
                    print(f"[WARNING] Ошибка загрузки {file_path}: {e}")

            raw_words_by_level[level] = list(set(combined))
            
        for level, words in raw_words_by_level.items():
             if words:
                 self.words_decks[level] = WordDeck(words)
        
        # Если совсем нет слов, добавим заглушку, чтобы бот не падал при старте
        if not self.words_decks.get("easy"):
            print("[WARNING] Не найдено слов! Используем резервные.")
            self.words_decks["easy"] = WordDeck(["крокодил", "солнце", "дерево"])

    def get_random_word(self, level: str = "easy") -> str:
        if level not in self.words_decks:
            level = "easy"
        deck = self.words_decks.get(level) or self.words_decks.get("easy")
        if not deck:
             raise RuntimeError(f"Нет слов для уровня {level}")
        return deck.get_word()

    # ==========================================================
    #                            ИГРА
    # ==========================================================

    async def start_round(self, chat_id: int, leader_id: int, leader_name: str, duration: int = None, level: str = "easy") -> str:
        duration = duration or self.DEFAULT_DURATION

        # Статистика сохраняется под ключом ID чата
        self._ensure_user(chat_id, leader_id, leader_name)
        self.stats[str(chat_id)][str(leader_id)]["led"] += 1
        self._save_stats()

        if chat_id in self.chats and self.chats[chat_id].get("task"):
            self.chats[chat_id]["task"].cancel()

        word = self.get_random_word(level)
        task = asyncio.create_task(self._timeout(chat_id, duration, self.bot)) 

        self.chats[chat_id] = {
            "leader_id": leader_id,
            "leader_name": leader_name,
            "word": word,
            "guessed": False,
            "task": task,
            "duration": duration,
            "level": level
        }
        return word

    async def _timeout(self, chat_id: int, duration: int, bot_instance):
        if not bot_instance: return

        try:
            await asyncio.sleep(duration - 60)
            session = self.chats.get(chat_id)
            if session and not session["guessed"]:
                await bot_instance.send_message(chat_id, "⏱ Осталась 1 минута!")

            await asyncio.sleep(60)
            session = self.chats.get(chat_id)
            if not session or session["guessed"]:
                return

            leader_id = session["leader_id"]
            
            # Запись проигрыша
            self._ensure_user(chat_id, leader_id)
            self.stats[str(chat_id)][str(leader_id)]["failed"] += 1
            self._save_stats()

            await bot_instance.send_message(
                chat_id,
                f"💀 @{session['leader_name']} проиграл!\nСлово было: <b>{session['word']}</b>",
                parse_mode="HTML"
            )
            del self.chats[chat_id]

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[ERROR] Timeout error: {e}")

    async def change_word(self, chat_id: int) -> Optional[str]:
        session = self.chats.get(chat_id)
        if not session: return None

        level = session.get("level", "easy")
        try:
            session["word"] = self.get_random_word(level)
        except RuntimeError:
            return None

        session["guessed"] = False
        if session.get("task"): session["task"].cancel()
        session["task"] = asyncio.create_task(self._timeout(chat_id, session["duration"], self.bot))
        return session["word"]

    async def register_guess(self, chat_id: int, user_id: int, username: str, text: str):
        session = self.chats.get(chat_id)
        if not session or session["guessed"]: return None
        if user_id == session["leader_id"]: return None

        if text.strip().lower() == session["word"].lower():
            session["guessed"] = True
            if session.get("task"): session["task"].cancel()

            # Запись выигрыша
            self._ensure_user(chat_id, user_id, username)
            self.stats[str(chat_id)][str(user_id)]["guessed"] += 1
            self._save_stats()
            
            del self.chats[chat_id] 
            return {"word": session["word"], "user_id": user_id, "username": username}
        return None

    async def ask_to_be_leader(self, chat_id: int, user_id: int, username: str, duration: int = None) -> str:
        level = "easy"
        if chat_id in self.chats:
            level = self.chats[chat_id].get("level", "easy")
        
        return await self.start_round(
            chat_id=chat_id,
            leader_id=user_id,
            leader_name=username,
            duration=duration,
            level=level
        )