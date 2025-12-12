FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# копируем зависимости бота
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# копируем все остальные файлы
COPY . .

CMD ["python", "bot_runner.py"]
