FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Сначала копируем requirements.txt из корня проекта
COPY requirements.txt .

RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Копируем саму папку бота
COPY telegram_bot/ ./telegram_bot/

WORKDIR /app/telegram_bot

CMD ["python", "bot_runner.py"]
