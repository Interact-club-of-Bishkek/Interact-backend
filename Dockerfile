FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# ИЗМЕНЕНО: Рабочий каталог теперь /app
WORKDIR /app

# Устанавливаем необходимые пакеты
# netcat-traditional добавлен, чтобы обеспечить работу команды 'nc' в entrypoint.sh
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

EXPOSE 8000

# КОМАНДА ЗАПУСКА УДАЛЕНА: Мы будем использовать скрипт entrypoint
# CMD ["gunicorn", "interact.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]