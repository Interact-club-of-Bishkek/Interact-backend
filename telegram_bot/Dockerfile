# Dockerfile должен лежать в папке Interact-backend/
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# 1. Устанавливаем зависимости для сборки
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential \
        libsm6 \
        libxext6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. Устанавливаем зависимости (Копируем файл из корня сборки)
WORKDIR /tmp
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
# Очистка временной директории
RUN rm requirements.txt

# 3. Копируем ВЕСЬ код в /app/telegram_bot
WORKDIR /app
# Копируем всю папку telegram_bot целиком
COPY telegram_bot ./telegram_bot 

# 4. Устанавливаем рабочую директорию для запуска
WORKDIR /app/telegram_bot

# Запуск бота (должен быть запущен из папки telegram_bot, чтобы импорты работали)
CMD ["python", "bot_runner.py"]