import random
import asyncio
import json
from pathlib import Path
from typing import Dict, Optional

# ---------- PATHS ----------
BASE_DIR = Path(__file__).resolve().parent
STATS_FILE = BASE_DIR / "crocodile_stats.json"
CACHE_DIR = BASE_DIR / "cache_words"
CACHE_DIR.mkdir(exist_ok=True)

# ---------- УРОВНИ ----------
LEVELS = {
    "easy": ["nouns"],                     # только существительные
    "medium": ["nouns", "adjectives"],     # сущ + прил
    "hard": ["nouns", "adjectives", "verbs"]  # сущ + прил + глаголы
}


class CrocodileManager:
    def __init__(self):
        self.chats: Dict[int, dict] = {}
        self.stats: Dict[int, dict] = {}
        self.words: Dict[str, list[str]] = {}
        self.bot = None

        self._load_stats()
        self._load_words_from_cache()

    # ==========================================================
    #                         СТАТИСТИКА
    # ==========================================================

    def _load_stats(self):
        if STATS_FILE.exists():
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
                self.stats = {int(k): v for k, v in raw.items()}
        else:
            self.stats = {}

    def _save_stats(self):
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {str(k): v for k, v in self.stats.items()},
                f,
                ensure_ascii=False,
                indent=2
            )

    def _ensure_user(self, user_id: int, name: Optional[str] = None):
        if user_id not in self.stats:
            self.stats[user_id] = {
                "name": name or f"ID {user_id}",
                "led": 0,
                "guessed": 0,
                "failed": 0
            }
        elif name:
            self.stats[user_id]["name"] = name

    # ==========================================================
    #                           СЛОВА
    # ==========================================================

    def _load_words_from_cache(self):
        """
        Загружает слова из:
        cache_words/
            nouns/summary.json
            adjectives/summary.json
            verbs/summary.json
        """
        self.words = {}

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
                            if isinstance(w, str) and w.isalpha()
                        )
                except Exception as e:
                    print(f"[WARNING] Ошибка загрузки {file_path}: {e}")

            random.shuffle(combined)
            self.words[level] = combined
            print(f"[INFO] Уровень {level}: {len(combined)} слов")

        if not self.words.get("easy"):
            raise RuntimeError("❌ Нет слов даже для уровня easy")

    def get_random_word(self, level: str = "easy") -> str:
        if level not in self.words or not self.words[level]:
            level = "easy"

        if not self.words[level]:
            raise RuntimeError(f"Нет слов для уровня {level}")

        return random.choice(self.words[level])

    # ==========================================================
    #                           ИГРА
    # ==========================================================

    async def start_round(
        self,
        chat_id: int,
        leader_id: int,
        leader_name: str,
        duration: int = 300,
        level: str = "easy"
    ) -> str:

        self._ensure_user(leader_id, leader_name)
        self.stats[leader_id]["led"] += 1
        self._save_stats()

        # Останавливаем старый таймер
        if chat_id in self.chats and self.chats[chat_id].get("task"):
            self.chats[chat_id]["task"].cancel()

        word = self.get_random_word(level)
        task = asyncio.create_task(self._timeout(chat_id, duration))

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

    async def _timeout(self, chat_id: int, duration: int):
        try:
            await asyncio.sleep(duration - 60)

            session = self.chats.get(chat_id)
            if session and not session["guessed"]:
                await self.bot.send_message(chat_id, "⏱ Осталась 1 минута!")

            await asyncio.sleep(60)

            session = self.chats.get(chat_id)
            if not session or session["guessed"]:
                return

            leader_id = session["leader_id"]
            self._ensure_user(leader_id)
            self.stats[leader_id]["failed"] += 1
            self._save_stats()

            await self.bot.send_message(
                chat_id,
                f"💀 @{session['leader_name']} проиграл!\n"
                f"Слово было: {session['word']}"
            )

            del self.chats[chat_id]

        except asyncio.CancelledError:
            pass

    async def change_word(self, chat_id: int) -> Optional[str]:
        session = self.chats.get(chat_id)
        if not session:
            return None

        level = session.get("level", "easy")
        session["word"] = self.get_random_word(level)
        session["guessed"] = False

        if session.get("task"):
            session["task"].cancel()

        session["task"] = asyncio.create_task(
            self._timeout(chat_id, session["duration"])
        )

        return session["word"]

    async def register_guess(
        self,
        chat_id: int,
        user_id: int,
        username: str,
        text: str
    ):
        session = self.chats.get(chat_id)

        if not session or session["guessed"]:
            return None

        # 🚫 Ведущий НЕ может угадывать
        if user_id == session["leader_id"]:
            return None

        if text.strip().lower() == session["word"].lower():
            session["guessed"] = True

            if session.get("task"):
                session["task"].cancel()

            self._ensure_user(user_id, username)
            self.stats[user_id]["guessed"] += 1
            self._save_stats()

            return {
                "word": session["word"],
                "user_id": user_id,
                "username": username
            }

        return None

    # ==========================================================
    #                    СМЕНА ВЕДУЩЕГО
    # ==========================================================

    async def ask_to_be_leader(
        self,
        chat_id: int,
        user_id: int,
        username: str,
        duration: int = 300
    ) -> str:
        """
        Делает пользователя ведущим и запускает новый раунд
        с текущим уровнем сложности.
        """

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
