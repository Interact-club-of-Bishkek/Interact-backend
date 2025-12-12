FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Копируем requirements.txt бота
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы
COPY . .

# Запуск бота
CMD ["python", "bot_runner.py"]
