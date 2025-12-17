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

# 2. Устанавливаем зависимости
WORKDIR /tmp
# КОПИРУЕТ requirements.txt из Interact-backend/ в /tmp в контейнере
COPY requirements.txt . 
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN rm requirements.txt

# 3. Копируем ВЕСЬ код
WORKDIR /app
# КОПИРУЕТ папку telegram_bot из Interact-backend/ в /app/telegram_bot в контейнере
COPY telegram_bot ./telegram_bot 

# 4. Устанавливаем рабочую директорию для запуска
# Заходим в папку, где лежит bot_runner.py
WORKDIR /app/telegram_bot

# Запуск бота
CMD ["python", "bot_runner.py"]