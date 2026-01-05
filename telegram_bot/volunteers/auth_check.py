import requests
import os
import asyncio
import logging

# Автоматически подтягиваем URL и исправляем его формат
DJANGO_BASE_URL = os.getenv("DJANGO_API_BASE_URL", "http://backend:8000/api/")
# Гарантируем правильный адрес: убираем лишние слэши и добавляем нужный в конце
BOT_AUTH_URL = f"{DJANGO_BASE_URL.rstrip('/')}/bot-auth/"

async def verify_volunteer_password(access_type: str, entered_password: str) -> bool:
    payload = {
        "access_type": access_type,
        "password": entered_password
    }

    try:
        # json=payload — это самый важный момент. 
        # Он сам скажет серверу, что это данные для проверки пароля.
        response = await asyncio.to_thread(
            requests.post, 
            BOT_AUTH_URL, 
            json=payload, 
            timeout=5
        )

        # Если статус 200 — пароль подошел, всё остальное — отказ
        return response.status_code == 200

    except Exception as e:
        logging.error(f"Ошибка связи: {e}")
        return False