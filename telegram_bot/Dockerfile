FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Устанавливаем git и зависимости для сборки
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код бота
COPY . .

# Запуск бота
CMD ["python", "bot_runner.py"]
