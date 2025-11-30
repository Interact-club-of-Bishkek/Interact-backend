FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app/backend

# Устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем только requirements, чтобы кэшировать зависимости
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект, кроме media
COPY . .

# Создаем папки, которые будут смонтированы как volumes
RUN mkdir -p /app/media /app/staticfiles

EXPOSE 8000

CMD ["gunicorn", "interact.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
