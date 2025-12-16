import random
import asyncio
import json
from pathlib import Path
from typing import Dict, Optional, List

# ---------- PATHS ----------
BASE_DIR = Path(__file__).resolve().parent
STATS_FILE = BASE_DIR / "crocodile_stats.json"
CACHE_DIR = BASE_DIR / "cache_words"
CACHE_DIR.mkdir(exist_ok=True)

# ---------- УРОВНИ ----------
LEVELS = {
    "easy": ["nouns"], 					    # только существительные
    "medium": ["nouns", "adjectives"], 		# сущ + прил
    "hard": ["nouns", "adjectives", "verbs"] 	# сущ + прил + глаголы
}

# ---------- КОЛОДЫ СЛОВ ----------
# Словарь для хранения "колод" слов, из которых будем брать слова, 
# чтобы избежать повторений в короткой серии игр.
class WordDeck:
    def __init__(self, all_words: List[str]):
        self._all_words = all_words
        self._deck = list(all_words)
        random.shuffle(self._deck)

    def get_word(self) -> str:
        if not self._deck:
            # Если колода пуста, перемешиваем все слова и пополняем
            self._deck = list(self._all_words)
            random.shuffle(self._deck)
            if not self._deck:
                 raise RuntimeError("Словарь пуст, не могу пополнить колоду.")
            print("[INFO] Колода слов пополнена и перемешана.")
            
        return self._deck.pop()

class CrocodileManager:
    def __init__(self):
        self.chats: Dict[int, dict] = {}
        self.stats: Dict[int, dict] = {}
        # Словарь для хранения объектов WordDeck по уровням сложности
        self.words_decks: Dict[str, WordDeck] = {} 
        self.bot = None
        self.DEFAULT_DURATION = 300 # 5 минут

        self._load_stats()
        self._load_words_from_cache()

    # ==========================================================
    #                         СТАТИСТИКА (Без изменений)
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
            # Обновляем имя, если оно изменилось
            self.stats[user_id]["name"] = name

    # ==========================================================
    #                           СЛОВА
    # ==========================================================

    def _load_words_from_cache(self):
        """
        Загружает слова и инициализирует WordDeck для каждого уровня.
        """
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
                            if isinstance(w, str) and w.isalpha() and len(w) > 2 # Убираем слишком короткие слова
                        )
                except Exception as e:
                    print(f"[WARNING] Ошибка загрузки {file_path}: {e}")

            raw_words_by_level[level] = list(set(combined)) # Удаляем дубликаты
            print(f"[INFO] Уровень {level}: {len(raw_words_by_level[level])} уникальных слов")
            
        # Инициализация колод
        for level, words in raw_words_by_level.items():
             if words:
                 self.words_decks[level] = WordDeck(words)
        
        if not self.words_decks.get("easy"):
            raise RuntimeError("❌ Нет слов даже для уровня easy")

    def get_random_word(self, level: str = "easy") -> str:
        """Получает слово из колоды соответствующего уровня, обеспечивая ротацию."""
        
        # Если уровня нет, берем easy
        if level not in self.words_decks:
            level = "easy"
            
        deck = self.words_decks.get(level)
        if not deck:
            # Fallback на easy, если основная колода не инициализирована
            deck = self.words_decks.get("easy")
        
        if not deck:
             raise RuntimeError(f"Нет слов для уровня {level}")
             
        return deck.get_word()


    # ==========================================================
    #                           ИГРА
    # ==========================================================

    async def start_round(
        self,
        chat_id: int,
        leader_id: int,
        leader_name: str,
        duration: int = None, # Используем стандартное значение, если не передано
        level: str = "easy"
    ) -> str:
        
        duration = duration or self.DEFAULT_DURATION

        self._ensure_user(leader_id, leader_name)
        self.stats[leader_id]["led"] += 1
        self._save_stats()

        # Останавливаем старый таймер, если есть
        if chat_id in self.chats and self.chats[chat_id].get("task"):
            self.chats[chat_id]["task"].cancel()

        word = self.get_random_word(level)
        
        # Передаем bot в _timeout, чтобы не было ошибки, если self.bot=None
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
        
        # ⚠️ ИСПРАВЛЕНИЕ: Проверяем, есть ли бот для отправки сообщений
        if not bot_instance:
             print(f"[ERROR] Бот не был передан в CrocodileManager! Таймер не может отправлять сообщения.")
             # Не завершаем раунд, но не отправляем сообщения
             try:
                 await asyncio.sleep(duration)
             except asyncio.CancelledError:
                 pass
             return


        try:
            # Первое ожидание (до 1 минуты до конца)
            await asyncio.sleep(duration - 60)

            session = self.chats.get(chat_id)
            if session and not session["guessed"]:
                await bot_instance.send_message(chat_id, "⏱ Осталась 1 минута!")

            # Второе ожидание (финальная минута)
            await asyncio.sleep(60)

            session = self.chats.get(chat_id)
            if not session or session["guessed"]:
                return

            leader_id = session["leader_id"]
            self._ensure_user(leader_id)
            self.stats[leader_id]["failed"] += 1
            self._save_stats()

            await bot_instance.send_message(
                chat_id,
                f"💀 @{session['leader_name']} проиграл!\n"
                f"Слово было: **{session['word']}**"
            )

            del self.chats[chat_id]

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[ERROR] Ошибка в таймауте для {chat_id}: {e}")

    async def change_word(self, chat_id: int) -> Optional[str]:
        session = self.chats.get(chat_id)
        if not session:
            return None

        level = session.get("level", "easy")
        
        # 🔄 Используем новый метод, чтобы получить слово из колоды
        try:
            session["word"] = self.get_random_word(level)
        except RuntimeError:
            return None # Если слова закончились

        session["guessed"] = False

        if session.get("task"):
            session["task"].cancel()

        # ⚠️ ИСПРАВЛЕНИЕ: Перезапускаем таймаут
        session["task"] = asyncio.create_task(
            self._timeout(chat_id, session["duration"], self.bot)
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

        # 🔍 Упрощенная проверка: угадывание должно быть точным совпадением (без учета регистра)
        if text.strip().lower() == session["word"].lower():
            session["guessed"] = True

            if session.get("task"):
                session["task"].cancel()

            self._ensure_user(user_id, username)
            self.stats[user_id]["guessed"] += 1
            self._save_stats()
            
            # Удаляем игру после угадывания
            del self.chats[chat_id] 

            return {
                "word": session["word"],
                "user_id": user_id,
                "username": username
            }

        return None

    # ==========================================================
    #                    СМЕНА ВЕДУЩЕГО
    # ==========================================================

    async def ask_to_be_leader(
        self,
        chat_id: int,
        user_id: int,
        username: str,
        duration: int = None
    ) -> str:
        """
        Делает пользователя ведущим и запускает новый раунд
        с текущим уровнем сложности.
        """
        
        duration = duration or self.DEFAULT_DURATION

        level = "easy"
        if chat_id in self.chats:
            level = self.chats[chat_id].get("level", "easy")
        
        # ⚠️ НОВЫЙ ЛОГИЧЕСКИЙ ШАГ: 
        # Если слово было угадано в предыдущем раунде, игра уже должна быть удалена из self.chats 
        # (см. register_guess). Но если мы вызываем ask_to_be_leader после тайм-аута,
        # session может отсутствовать. start_round инициирует новый раунд, 
        # используя уровень из прошлого сеанса, если возможно.
        
        return await self.start_round(
            chat_id=chat_id,
            leader_id=user_id,
            leader_name=username,
            duration=duration,
            level=level
        )