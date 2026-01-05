import io
import requests
import asyncio
import os
import re
import logging
from datetime import datetime
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

# Конфигурация API
DJANGO_API_BASE_URL = os.getenv("DJANGO_API_URL", "http://127.0.0.1:8000/api/")
# Важно: В Django в конце URL должен быть слеш /
PROJECT_CREATE_ENDPOINT = f"{DJANGO_API_BASE_URL}projects/create"
DIRECTIONS_API_URL = f"{DJANGO_API_BASE_URL}project-directions/"

class ProjectCreateSteps(StatesGroup):
    waiting_name = State()
    waiting_title = State()
    waiting_direction = State()
    waiting_category = State()
    waiting_price = State()
    waiting_phone = State()
    waiting_address = State()
    waiting_time_start = State()
    waiting_time_end = State()
    waiting_image = State()

# --- Вспомогательные функции валидации ---

def is_valid_datetime(date_str):
    try:
        # Проверяем строгий формат, который ожидает Django
        datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False

async def fetch_directions():
    try:
        response = await asyncio.to_thread(requests.get, DIRECTIONS_API_URL, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logging.error(f"Ошибка при получении направлений: {e}")
    return []

# --- Логика сбора данных ---

@router.message(ProjectCreateSteps.waiting_name)
async def process_name(message: types.Message, state: FSMContext):
    if len(message.text) < 3:
        return await message.answer("❌ Название слишком короткое. Введите нормальное название проекта:")
    await state.update_data(name=message.text)
    await state.set_state(ProjectCreateSteps.waiting_title)
    await message.answer("📝 Введите <b>описание</b> проекта:", parse_mode="HTML")

@router.message(ProjectCreateSteps.waiting_title)
async def process_title(message: types.Message, state: FSMContext):
    if len(message.text) < 10:
        return await message.answer("❌ Описание слишком короткое. Расскажите о проекте подробнее:")
    
    await state.update_data(title=message.text)
    directions = await fetch_directions()
    
    if not directions:
        await message.answer("⚠️ Не удалось загрузить направления из базы. Введите ID направления вручную (число):")
        await state.set_state(ProjectCreateSteps.waiting_direction)
        return

    builder = []
    for dir_obj in directions:
        builder.append([InlineKeyboardButton(text=dir_obj['name'], callback_data=f"pdir_{dir_obj['id']}")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=builder)
    await state.set_state(ProjectCreateSteps.waiting_direction)
    await message.answer("📂 Выберите <b>направление</b> проекта:", reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("pdir_"), ProjectCreateSteps.waiting_direction)
async def process_direction_select(call: types.CallbackQuery, state: FSMContext):
    direction_id = call.data.split("_")[1]
    await state.update_data(direction_id=direction_id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚽ Спорт", callback_data="pcat_sport")],
        [InlineKeyboardButton(text="🎮 Киберспорт", callback_data="pcat_cyber_sport")],
        [InlineKeyboardButton(text="🎓 Образование", callback_data="pcat_education")],
        [InlineKeyboardButton(text="💰 Фандрайзинг", callback_data="pcat_fundraising")],
        [InlineKeyboardButton(text="🎭 Культура", callback_data="pcat_cultural")]
    ])
    
    await state.set_state(ProjectCreateSteps.waiting_category)
    await call.message.edit_text("📂 Теперь выберите <b>категорию</b>:", reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("pcat_"), ProjectCreateSteps.waiting_category)
async def process_category_select(call: types.CallbackQuery, state: FSMContext):
    category = call.data.split("_", 1)[1]
    await state.update_data(category=category)
    await state.set_state(ProjectCreateSteps.waiting_price)
    await call.message.edit_text("💰 Введите <b>цену</b> (только цифры, 0 если бесплатно):", parse_mode="HTML")
    await call.answer()

@router.message(ProjectCreateSteps.waiting_price)
async def process_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ Ошибка! Введите числовое значение (например: 500):")
    
    await state.update_data(price=int(message.text))
    await state.set_state(ProjectCreateSteps.waiting_phone)
    await message.answer("📞 Введите <b>номер телефона</b> для связи (например, +996...):", parse_mode="HTML")

@router.message(ProjectCreateSteps.waiting_phone)
async def process_phone(message: types.Message, state: FSMContext):
    # Базовая проверка номера телефона
    if not re.match(r"^\+?[\d\s\-]{9,15}$", message.text):
        return await message.answer("❌ Некорректный номер. Используйте формат: +996700123456")
    
    await state.update_data(phone_number=message.text)
    await state.set_state(ProjectCreateSteps.waiting_address)
    await message.answer("📍 Введите <b>адрес</b> проведения проекта:", parse_mode="HTML")

@router.message(ProjectCreateSteps.waiting_address)
async def process_address(message: types.Message, state: FSMContext):
    if len(message.text) < 3:
        return await message.answer("❌ Слишком короткий адрес.")
    
    await state.update_data(address=message.text)
    await state.set_state(ProjectCreateSteps.waiting_time_start)
    await message.answer("🕒 Введите <b>дату и время начала</b>\nФормат: <code>2026-01-10 18:00:00</code>", parse_mode="HTML")

@router.message(ProjectCreateSteps.waiting_time_start)
async def process_time_start(message: types.Message, state: FSMContext):
    if not is_valid_datetime(message.text):
        return await message.answer("❌ Неверный формат! Введите дату строго по образцу: <code>2026-01-10 18:00:00</code>", parse_mode="HTML")
    
    await state.update_data(time_start=message.text)
    await state.set_state(ProjectCreateSteps.waiting_time_end)
    await message.answer("🕒 Введите <b>дату и время конца</b> (в том же формате):", parse_mode="HTML")

@router.message(ProjectCreateSteps.waiting_time_end)
async def process_time_end(message: types.Message, state: FSMContext):
    if not is_valid_datetime(message.text):
        return await message.answer("❌ Неверный формат даты!")
    
    data = await state.get_data()
    # Проверка: время конца должно быть позже начала
    if message.text <= data['time_start']:
        return await message.answer("❌ Ошибка: Время окончания должно быть <b>позже</b> времени начала!")

    await state.update_data(time_end=message.text)
    await state.set_state(ProjectCreateSteps.waiting_image)
    await message.answer("🖼 Отправьте <b>обложку</b> проекта (одним фото):", parse_mode="HTML")

@router.message(ProjectCreateSteps.waiting_image, F.photo)
async def process_final_send(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    status_msg = await message.answer("⏳ Сохранение проекта, подождите...")

    photo_id = message.photo[-1].file_id
    file_info = await bot.get_file(photo_id)
    buffer = io.BytesIO()
    await bot.download_file(file_info.file_path, destination=buffer)
    buffer.seek(0)
    
    files = {'image': ('project.jpg', buffer.read(), 'image/jpeg')}
    
    # Ключи должны строго совпадать с полями в Django Serializer
    submit_data = {
        "name": data['name'],
        "title": data['title'],
        "category": data['category'],
        "price": data['price'],
        "phone_number": data['phone_number'],
        "address": data['address'],
        "time_start": data['time_start'],
        "time_end": data['time_end'],
        "direction_id": data.get('direction_id') 
    }

    try:
        response = await asyncio.to_thread(
            requests.post, PROJECT_CREATE_ENDPOINT, data=submit_data, files=files, timeout=20
        )
        
        if response.status_code in [200, 201]:
            await status_msg.edit_text("🚀 <b>Проект успешно создан!</b>", parse_mode="HTML")
            await state.clear()
        else:
            # Проверяем, не HTML ли пришел в ответ
            content_type = response.headers.get('Content-Type', '')
            
            if 'text/html' in content_type:
                await status_msg.edit_text(f"❌ <b>Ошибка сервера (HTML):</b> Код {response.status_code}. Проверьте URL эндпоинта.")
            else:
                # Если это JSON ошибка от DRF, выводим её аккуратно
                error_text = response.text[:200]
                await status_msg.edit_text(f"❌ <b>Ошибка API ({response.status_code}):</b>\n<code>{error_text}</code>", parse_mode="HTML")
                
    except Exception as e:
        # Здесь мы убираем parse_mode="HTML", так как в тексте ошибки 'e' могут быть < >
        await status_msg.edit_text(f"❌ Ошибка соединения: {str(e)}")