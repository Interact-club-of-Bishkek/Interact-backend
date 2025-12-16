FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочий каталог в корень приложения
WORKDIR /app

# Устанавливаем необходимые системные пакеты
# netcat-traditional нужен для скрипта entrypoint.sh для ожидания БД
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
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем не-root пользователя для запуска Gunicorn
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app

# ИСПРАВЛЕНИЕ: Установка прав доступа для томов
# Это гарантирует, что appuser может создавать/изменять файлы в /app/media и /app/staticfiles
RUN chmod -R 775 /app/media
RUN chmod -R 775 /app/staticfiles

EXPOSE 8000

# CMD удалена, так как запуск осуществляется через entrypoint.sh