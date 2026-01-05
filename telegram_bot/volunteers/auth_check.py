import requests
import os
import asyncio
import logging

# URL вашего Django API: http://backend:8000/api/bot-auth/
DJANGO_BASE_URL = os.getenv("DJANGO_API_URL", 'http://127.0.0.1:8000/')
BOT_AUTH_URL = f"{DJANGO_BASE_URL}bot-auth/"

async def verify_volunteer_password(access_type: str, entered_password: str) -> bool:
    """
    access_type: 'commands' или 'add_project'
    """
    payload = {
        "access_type": access_type,
        "password": entered_password
    }

    try:
        # Используем thread для синхронного requests в асинхронном окружении
        response = await asyncio.to_thread(
            requests.post, 
            BOT_AUTH_URL, 
            data=payload, 
            timeout=5
        )

        if response.status_code == 200:
            return True
        return False

    except Exception as e:
        logging.error(f"Ошибка связи с API при проверке пароля: {e}")
        return False