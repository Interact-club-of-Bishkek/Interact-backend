FROM python:3.11-slim

# 1. Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    netcat-openbsd \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# 2. Рабочая директория
WORKDIR /app

# 3. Копируем файлы проекта
COPY . .

# 4. Создаем директории для статики/медиа и назначаем права
RUN mkdir -p /app/media /app/staticfiles && \
    adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app

# 5. Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 6. Устанавливаем зависимости
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# 7. Настройка entrypoint (исправление формата и прав)
RUN sed -i 's/\r$//' /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh && \
    chown appuser:appuser /app/entrypoint.sh

# 8. Переключаемся на пользователя
USER appuser

EXPOSE 8000

# 9. Запуск
ENTRYPOINT ["/app/entrypoint.sh"]