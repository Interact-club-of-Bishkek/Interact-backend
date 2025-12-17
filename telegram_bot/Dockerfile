FROM interact_base:latest

WORKDIR /app

# Копируем только папку бота (код бэкенда боту не нужен)
COPY telegram_bot ./telegram_bot

# Переходим в директорию запуска
WORKDIR /app/telegram_bot

# Запуск
CMD ["python", "bot_runner.py"]