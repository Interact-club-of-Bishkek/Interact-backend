# Используем Python 3.11 для совместимости
FROM python:3.11-slim

# Установка переменных окружения
ENV PYTHONUNBUFFERED=1

# Устанавливаем git и зависимости для сборки, сразу очищая кэш apt
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential \
        # Дополнительные зависимости для Pillow/OpenCV могут потребоваться
        libsm6 \
        libxext6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем ЕДИНСТВЕННЫЙ requirements.txt из корня
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --upgrade pip
# Используем --no-cache-dir для экономии места
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код бота (теперь все зависимости уже установлены)
# Убедитесь, что у вас есть .dockerignore, чтобы не копировать лишнее!
COPY . .

# Запуск бота
CMD ["python", "bot_runner.py"]