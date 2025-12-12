import random
import asyncio
import time
import json
from typing import Dict, Optional
from .word_parser import preprocess_words

STATS_FILE = "crocodile_stats.json"
WORDS_FILE = "russian.txt"

class CrocodileManager:
    def __init__(self):
        self.chats: Dict[int, dict] = {}
        self.stats = {}
        self.words: list[str] = []
        self.bot = None
        self._load_stats()

    def _load_stats(self):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                self.stats = json.load(f)
        except:
            self.stats = {}

    def _save_stats(self):
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

    def _ensure_user_stats(self, user_id: int, username: str = None):
        if str(user_id) not in self.stats:
            self.stats[str(user_id)] = {"led":0, "guessed":0, "failed":0, "name": username or f"ID {user_id}"}
        else:
            if username:
                self.stats[str(user_id)]["name"] = username

    def load_words(self):
        self.words = preprocess_words(WORDS_FILE)
        print(f"[INFO] Загружено {len(self.words)} слов для игры")

    def get_random_word(self) -> str:
        if not self.words:
            return "слово"
        return random.choice(self.words)

    async def start_round(self, chat_id:int, leader_id:int, leader_name:str, duration:int=300):
        word = self.get_random_word()
        self._ensure_user_stats(leader_id, leader_name)
        self.stats[str(leader_id)]["led"] += 1
        self._save_stats()

        session = self.chats.get(chat_id)
        if session and session.get("task"):
            session["task"].cancel()

        task = asyncio.create_task(self._timeout_task(chat_id, duration))
        self.chats[chat_id] = {
            "leader_id": leader_id,
            "leader_name": leader_name,
            "word": word,
            "start_at": time.time(),
            "guessed": False,
            "duration": duration,
            "task": task
        }
        return word

    async def _timeout_task(self, chat_id:int, duration:int):
        try:
            # напоминание за минуту
            await asyncio.sleep(duration - 60)
            session = self.chats.get(chat_id)
            if session and not session["guessed"]:
                await self.bot.send_message(chat_id, "⏱ Осталась 1 минута!")

            await asyncio.sleep(60)
            session = self.chats.get(chat_id)
            if not session or session["guessed"]:
                return
            leader_id = session["leader_id"]
            self._ensure_user_stats(leader_id)
            self.stats[str(leader_id)]["failed"] += 1
            self._save_stats()
            await self.bot.send_message(chat_id, f"💀 @{session['leader_name']} проиграл! Слово было: {session['word']}")
            del self.chats[chat_id]
        except asyncio.CancelledError:
            pass

    async def change_word(self, chat_id:int) -> Optional[str]:
        session = self.chats.get(chat_id)
        if not session:
            return None
        new_word = self.get_random_word()
        session["word"] = new_word
        session["start_at"] = time.time()
        if session.get("task"):
            session["task"].cancel()
        session["task"] = asyncio.create_task(self._timeout_task(chat_id, session["duration"]))
        session["guessed"] = False
        return new_word

    async def register_guess(self, chat_id:int, user_id:int, username:str, text:str):
        session = self.chats.get(chat_id)
        if not session or session["guessed"]:
            return None
        if text.strip().lower() == session["word"].strip().lower():
            session["guessed"] = True
            if session.get("task"):
                session["task"].cancel()
            self._ensure_user_stats(user_id, username)
            self.stats[str(user_id)]["guessed"] += 1
            self._save_stats()
            return {"word": session["word"], "user_id": user_id, "username": username}
        return None

    async def ask_to_be_leader(self, chat_id:int, user_id:int, username:str):
        return await self.start_round(chat_id, user_id, username)
