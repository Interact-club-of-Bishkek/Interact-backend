FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочий каталог в корень приложения
WORKDIR /app

# Устанавливаем необходимые системные пакеты
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libpq-dev \
    gosu \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Копируем только requirements, чтобы кэшировать зависимости
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
# Копируем весь проект
COPY . .

# Создаем пустые директории для томов. (Решает проблему сборки)
RUN mkdir -p /app/media /app/staticfiles

# Создаем не-root пользователя для запуска Gunicorn
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app

# Установка прав доступа для созданных директорий в образе
RUN chmod -R 775 /app/media
RUN chmod -R 775 /app/staticfiles

EXPOSE 8000