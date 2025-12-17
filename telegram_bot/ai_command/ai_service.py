import os
import pickle
import numpy as np
import faiss
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

# Настройки путей
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Путь к PDF относительно корня (telegram_bot/)
PDF_PATH = os.path.join(BASE_DIR, "rules.pdf") 
# Пути к индексам внутри текущей папки (ai_command/)
INDEX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
INDEX_FILE = os.path.join(INDEX_DIR, "faiss_index.bin")
CHUNKS_FILE = os.path.join(INDEX_DIR, "chunks.pkl")

class AIService:
    def __init__(self):
        self.index = None
        self.chunks = []
        self.is_initialized = False
        
        # 1. Инициализация модели эмбеддингов (HuggingFace)
        print("📥 Инициализация модели SentenceTransformer...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # 2. Инициализация клиента Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("❌ ОШИБКА: Не найден GROQ_API_KEY в .env файле!")
        
        self.client = AsyncGroq(api_key=api_key)

    async def initialize(self):
        """Асинхронная инициализация, загружающая или создающая базу."""
        if self.is_initialized:
            return

        # 3. Загрузка базы
        if os.path.exists(INDEX_FILE) and os.path.exists(CHUNKS_FILE):
            try:
                self.index = faiss.read_index(INDEX_FILE)
                with open(CHUNKS_FILE, "rb") as f:
                    self.chunks = pickle.load(f)
                print(f"✅ База загружена: {self.index.ntotal} фрагментов.")
                self.is_initialized = True
            except Exception as e:
                print(f"⚠️ Ошибка загрузки базы: {e}. Запуск обучения.")
                # Если загрузка не удалась, запускаем обучение (синхронно, в отдельном потоке)
                import asyncio
                await asyncio.to_thread(self.build_index)
                self.is_initialized = True
        else:
            print("⚠️ База не найдена. Запуск обучения.")
            # Запускаем обучение (синхронно, в отдельном потоке)
            import asyncio
            await asyncio.to_thread(self.build_index)
            self.is_initialized = True
            
    def _split_text(self, text, chunk_size=1000, overlap=200):
        """Простая функция для разбивки текста на части с перекрытием"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += chunk_size - overlap
        return chunks

    def build_index(self):
        """Создание базы знаний с нуля (СИНХРОННО)"""
        if not os.path.exists(PDF_PATH):
            return f"❌ Файл PDF не найден по пути: {PDF_PATH}"

        print("🔄 Начало индексации PDF...")
        try:
            reader = PdfReader(PDF_PATH)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            if not text:
                return "❌ PDF пустой или не содержит текста."

            self.chunks = self._split_text(text)
            print(f"📄 Текст разбит на {len(self.chunks)} частей. Генерация векторов...")

            embeddings = self.embedder.encode(self.chunks)
            
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
            self.index.add(np.array(embeddings).astype('float32'))

            faiss.write_index(self.index, INDEX_FILE)
            with open(CHUNKS_FILE, "wb") as f:
                pickle.dump(self.chunks, f)

            return "База знаний успешно обновлена."

        except Exception as e:
            return f"❌ Ошибка: {e}"

    async def get_answer(self, query: str):
        """Поиск ответа (АСИНХРОННО)"""
        if not self.is_initialized:
            # Если бот не был инициализирован (хотя main() должен это сделать), ждем
            await self.initialize()

        if not self.index or not self.chunks:
            return "❌ База знаний не готова. Файл rules.pdf отсутствует или пуст."

        try:
            query_vector = self.embedder.encode([query])
            
            # Увеличено k до 5 для надежного захвата контекста
            D, I = self.index.search(np.array(query_vector).astype('float32'), k=5) 
            
            found_texts = [self.chunks[i] for i in I[0] if i < len(self.chunks)]
            context = "\n\n".join(found_texts)

            system_prompt = (
                "Ты — полезный и точный ассистент Interact Club. Отвечай на русском языке. "
                "Твоя задача — извлечь ответ ТОЛЬКО из предоставленного КОНТЕКСТА. "
                "Если в КОНТЕКСТЕ есть точная информация (например, цифры или факты), ты ОБЯЗАН использовать ее. "
                "Если информации нет, ответь: 'К сожалению, в моих документах нет информации об этом'. "
                "Не придумывай факты. "
                "\n\n--- КОНТЕКСТ ---\n" + context
            )

            response = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                model="llama-3.1-8b-instant", # Актуальное имя модели Groq
                temperature=0.3,
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Ошибка ИИ: {e}"

# Создаем экземпляр сервиса
ai_bot = AIService()