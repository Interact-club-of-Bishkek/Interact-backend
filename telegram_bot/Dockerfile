FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY telegram_bot/ .

CMD ["python", "bot_runner.py"]
