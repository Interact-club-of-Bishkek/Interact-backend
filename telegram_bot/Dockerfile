FROM python:3.11

WORKDIR /app

COPY telegram_bot/ /app/

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "bot_runner.py"]
