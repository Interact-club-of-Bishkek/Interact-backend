FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app/backend

# Устанавливаем необходимые пакеты для psycopg2 и git
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# pip и установка зависимостей
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "interact.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
