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

EXPOSE 8000
# Entrypoint подхватится из docker-compose.yml