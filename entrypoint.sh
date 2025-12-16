#!/bin/bash

# Ожидание готовности базы данных
echo "Ожидание PostgreSQL..."

while ! nc -z db 5432; do
  sleep 0.1
done

echo "PostgreSQL запущен!"

# 1. Применение миграций (создание структуры БД или обновление)
# Это гарантирует, что база данных всегда актуальна
echo "Применение миграций Django..."
python manage.py migrate --noinput

# 2. Сбор статических файлов
echo "Сбор статических файлов..."
python manage.py collectstatic --noinput

# 3. Запуск Gunicorn (запускается от имени не-root пользователя appuser)
echo "Запуск Gunicorn..."
exec gosu appuser gunicorn interact.wsgi:application --bind 0.0.0.0:8000 --workers 3