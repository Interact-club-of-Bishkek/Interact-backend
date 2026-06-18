FROM interact_base:latest

WORKDIR /app

# Копируем весь код проекта
COPY . .

# Создаем директории для статики и медиа
RUN mkdir -p /app/media /app/staticfiles

# Настройка прав доступа и пользователя
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 775 /app/media /app/staticfiles

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Используем uv для установки зависимостей
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

EXPOSE 8000
# Entrypoint подхватится из docker-compose.yml
