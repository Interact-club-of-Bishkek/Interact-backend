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

# ... (Предыдущие строки до сюда остаются без изменений)

# Копируем весь проект
COPY . .

# Создаем пустые директории для статики и медиа, чтобы chmod мог работать
RUN mkdir -p /app/media /app/staticfiles

# Создаем не-root пользователя для запуска Gunicorn
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app

# ИСПРАВЛЕНИЕ: Установка прав доступа для созданных директорий
# Это предотвратит ошибки, если директории не монтируются
RUN chmod -R 775 /app/media
RUN chmod -R 775 /app/staticfiles

EXPOSE 8000
# CMD удалена, так как запуск осуществляется через entrypoint.sh