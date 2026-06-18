#!/bin/bash

# Ожидание базы данных
echo "Ожидание PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done
echo "PostgreSQL запущен!"

# Установка прав доступа (так как мы уже appuser, права должны быть настроены заранее)
# Если здесь будут ошибки "permission denied", значит chown нужно делать в Dockerfile
echo "Проверка прав доступа..."

# Подготовка
echo "Применение миграций Django..."
python manage.py migrate --noinput

echo "Сбор статических файлов..."
python manage.py collectstatic --noinput

# Запуск Gunicorn (теперь без gosu)
echo "Запуск Gunicorn..."
exec gunicorn interact.wsgi:application --bind 0.0.0.0:8000 --workers 3