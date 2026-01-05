import requests
import os
import asyncio
import logging

# 1. Получаем базу и гарантируем наличие протокола http/https
DJANGO_BASE_URL = os.getenv("DJANGO_API_URL", "http://backend:8000/api/")
if not DJANGO_BASE_URL.startswith(('http://', 'https://')):
    DJANGO_BASE_URL = f"http://{DJANGO_BASE_URL}"

# 2. Гарантируем закрывающий слеш, чтобы избежать 301 редиректа и ошибки 405
BOT_AUTH_URL = f"{DJANGO_BASE_URL.rstrip('/')}/bot-auth/"

async def verify_volunteer_password(access_type: str, entered_password: str) -> bool:
    payload = {
        "access_type": access_type,
        "password": entered_password
    }

    try:
        # 3. Используем json= вместо data= для корректной работы с APIView
        response = await asyncio.to_thread(
            requests.post, 
            BOT_AUTH_URL, 
            json=payload,  # <-- ВАЖНО: передаем как JSON
            timeout=5
        )

        # Логируем для отладки, если что-то пойдет не так
        if response.status_code != 200:
            logging.warning(f"API returned {response.status_code}: {response.text}")

        return response.status_code == 200

    except Exception as e:
        logging.error(f"Ошибка связи с API при проверке пароля: {e}")
        return False