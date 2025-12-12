FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# копируем только requirements из родителя
COPY ../requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# копируем весь код бота
COPY . .

CMD ["python", "bot_runner.py"]
