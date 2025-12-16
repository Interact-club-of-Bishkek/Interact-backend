import asyncio
import logging
import requests
import os
import re
import io 
from datetime import datetime, timezone, timedelta 

# Импорт TelegramBadRequest для более точной обработки ошибок при редактировании
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest 
# ---> ИСПРАВЛЕНИЕ: Импорт StateFilter для корректной работы хендлера /cancel
from aiogram.filters.state import StateFilter
from dotenv import load_dotenv

load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Константы часового пояса Бишкека (GMT+6)
BISHKEK_TIMEZONE = timezone(timedelta(hours=6))

# ----------------------------------------------------------------------
# --- КОНФИГУРАЦИЯ ВРЕМЕННЫХ ЛИМИТОВ РЕГИСТРАЦИИ (GMT+6) ---
# --- Введите время в формате YYYY, MM, DD, HH, MM, SS                  ---
# ----------------------------------------------------------------------

REGISTRATION_START = datetime(2025, 12, 16, 0, 0, 0).replace(tzinfo=BISHKEK_TIMEZONE)
REGISTRATION_END = datetime(2026, 1, 4, 0, 0, 0).replace(tzinfo=BISHKEK_TIMEZONE)

# Функция для получения текущего времени с учетом часового пояса (GMT+6)
def get_current_time_aware():
    return datetime.now(BISHKEK_TIMEZONE)

# --- КОНФИГУРАЦИЯ API И БОТА ---
# --- КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ 1: Использование имени сервиса Docker 'backend' вместо внешнего IP ---
# Считаем, что сервис Django в docker-compose назван 'backend'
DJANGO_API_BASE_URL = os.getenv("DJANGO_API_URL", "http://backend:8000/api/") 
APPLICATION_ENDPOINT = f"{DJANGO_API_BASE_URL}applications/"
DIRECTIONS_ENDPOINT = f"{DJANGO_API_BASE_URL}volunteer-directions/"

REQUEST_TIMEOUT = 10 

application_router = Router()
DIRECTIONS_CACHE = {} 

# --- КЛАВИАТУРЫ ---
YES_NO_KB = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Да ✅", callback_data="answer_yes"),
        InlineKeyboardButton(text="Нет ❌", callback_data="answer_no"),
    ]
])
SKIP_FEEDBACK_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Пропустить и отправить 🚀", callback_data="skip_feedback")]
])

WEEKLY_HOURS_KB = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="До 5 часов", callback_data="hours_5"),
        InlineKeyboardButton(text="5 - 10 часов", callback_data="hours_5_10"),
    ],
    [
        InlineKeyboardButton(text="10 - 15 часов", callback_data="hours_10_15"),
        InlineKeyboardButton(text="Более 15 часов", callback_data="hours_15_plus"),
    ],
    [
        InlineKeyboardButton(text="Свой вариант (ввести текстом) 📝", callback_data="hours_custom")
    ]
])

# Регулярные выражения для валидации
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
DATE_REGEX = r'^\d{4}-\d{2}-\d{2}$'


# --- МАШИНА СОСТОЯНИЙ (FSM) ---
class ApplicationSteps(StatesGroup):
    """Шаги для сбора данных анкеты волонтера (21 шаг)."""
    
    waiting_full_name = State()         
    waiting_phone_number = State()      
    waiting_email = State()             
    waiting_date_of_birth = State()     
    waiting_place_of_study = State()    
    waiting_photo = State()             

    waiting_why_volunteer = State()     
    waiting_volunteer_experience = State()
    waiting_hobbies_skills = State()    
    waiting_strengths = State()         

    waiting_directions = State()        
    waiting_choice_motives = State()    
    waiting_why_choose_you = State()    

    waiting_weekly_hours = State()      
    waiting_custom_weekly_hours = State() 
    waiting_attend_meetings = State()   
    waiting_expectations = State()      
    waiting_ideas_improvements = State()
    
    waiting_agree_inactivity_removal = State() 
    waiting_agree_terms = State()       
    waiting_ready_travel = State()      

    waiting_feedback = State()          


# --- ФУНКЦИИ ---
async def fetch_directions():
    """Загружает список направлений из Django API (кэширование)."""
    global DIRECTIONS_CACHE
    if DIRECTIONS_CACHE:
        return DIRECTIONS_CACHE
        
    try:
        response = await asyncio.to_thread(
            requests.get, DIRECTIONS_ENDPOINT, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        DIRECTIONS_CACHE = {
            d['id']: d['name'] for d in response.json()
        }
        return DIRECTIONS_CACHE
    except requests.RequestException as e:
        logging.error(f"Не удалось загрузить направления из API ({DIRECTIONS_ENDPOINT}): {e}")
        return {}


async def submit_application_to_django(bot, data: dict):
    """Отправляет данные анкеты и фото на Django API."""
    directions_ids = data.pop('selected_directions_ids', [])
    photo_file_id = data.pop('photo_file_id', None)
    
    submit_data = {
        "full_name": data.get('full_name'),
        "email": data.get('email'),
        "phone_number": data.get('phone_number'),
        "date_of_birth": data.get('date_of_birth', ''), 
        "place_of_study": data.get('place_of_study'),
        "why_volunteer": data.get('why_volunteer'),
        "volunteer_experience": data.get('volunteer_experience'),
        "hobbies_skills": data.get('hobbies_skills'),
        "strengths": data.get('strengths'),
        "why_choose_you": data.get('why_choose_you'),
        "expectations": data.get('expectations'),
        "ideas_improvements": data.get('ideas_improvements'),
        "directions": directions_ids, 
        "choice_motives": data.get('choice_motives'),
        "weekly_hours": data.get('weekly_hours'),
        "attend_meetings": data.get('attend_meetings', False),
        "agree_inactivity_removal": data.get('agree_inactivity_removal', False),
        "agree_terms": data.get('agree_terms', False),
        "ready_travel": data.get('ready_travel', False),
        "feedback": data.get('feedback'),
    }

    files = {}
    
    if photo_file_id:
        try:
            file_info = await bot.get_file(photo_file_id)
            file_path = file_info.file_path
            
            # Скачиваем файл в объект BytesIO
            file_stream = await bot.download_file(file_path, destination=io.BytesIO())
            
            # Используем getvalue() для надежной отправки байтов файла
            photo_bytes = file_stream.getvalue()
            
            # Собираем объект для requests.post. Имя поля 'photo' должно соответствовать модели Django.
            files['photo'] = ('volunteer_photo.jpg', photo_bytes, 'image/jpeg')
            logging.info("Фото успешно скачано и добавлено для отправки.") 
            
        except Exception as e:
            logging.error(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось загрузить или подготовить фото: {e}") 
            # В случае ошибки просто продолжаем без файла
            pass

    try:
        # Отправка данных и файла синхронно в отдельном потоке
        response = await asyncio.to_thread(
            requests.post, APPLICATION_ENDPOINT, data=submit_data, files=files, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status() 
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка API при отправке заявки: {e}")
        if 'response' in locals() and response.status_code == 400:
            # Выводим тело ответа 400 для лучшей диагностики
            logging.error(f"Детали ошибки API (400 Bad Request): {response.text}")
        return False


# --- ХЕНДЛЕР ОТМЕНЫ (CANCEL) ---
# ИСПРАВЛЕНИЕ: Используем StateFilter(ApplicationSteps)
@application_router.message(F.text.in_(['/cancel', 'Отмена', 'отмена']), StateFilter(ApplicationSteps))
@application_router.message(F.text == '/cancel', StateFilter(ApplicationSteps))
async def cancel_handler(message: types.Message, state: FSMContext):
    """Позволяет пользователю отменить заполнение анкеты."""
    current_state = await state.get_state()
    if current_state is None:
        return # Если нет активного FSM

    logging.info("Отмена анкеты: %s", current_state)
    await state.clear()
    
    await message.answer(
        "❌ <b>Заполнение анкеты отменено.</b>\n\n"
        "Вы можете начать заново, нажав на кнопку 'Подать заявку' (или аналогичную команду, которая запускает процесс).\n"
        "Если Вы ошиблись, начните с начала.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )

# --- ХЕНДЛЕРЫ ---

# 1. СТАРТ (С ПРОВЕРКОЙ ВРЕМЕНИ)
@application_router.callback_query(F.data == "volunteer_apply")
async def start_application(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    
    # 1. ПРОВЕРКА ВРЕМЕНИ РЕГИСТРАЦИИ
    now = get_current_time_aware()

    if now < REGISTRATION_START:
        # Регистрация еще не открыта (НЕТ ТОЧНОГО ВРЕМЕНИ)
        await call.answer(
            "Заявка еще закрыта. Следите за нашими новостями в Instagram, мы объявим, когда начнется набор.", 
            show_alert=True
        )
        return
    
    if now > REGISTRATION_END:
        # Регистрация уже закрыта
        await call.message.edit_text(
            "❌ <b>Регистрация закрыта.</b>\n\n"
            "К сожалению, время подачи заявок на волонтерство истекло. Спасибо за Ваш интерес! "
            "Следите за обновлениями, чтобы не пропустить следующий набор.",
            parse_mode="HTML"
        )
        await call.answer("Регистрация закрыта.", show_alert=True)
        return

    # Проверка, что чат приватный
    if call.message.chat.type != 'private':
        return await call.answer("Пожалуйста, начните заявку в личном чате с ботом.", show_alert=True)
        
    # Если время в диапазоне, продолжаем
    await call.message.edit_text(
        "📝 <b>Начало регистрации: Анкета волонтера Interact Club</b> 🌍\n\n"
        "Вам предстоит заполнить <b>21 шаг</b>. Все поля, кроме финального отзыва, обязательны.\n"
        "<b>Чтобы отменить анкету в любой момент, отправьте команду /cancel.</b>\n"
        "Пожалуйста, отвечайте полным текстом, чтобы мы могли лучше Вас узнать!",
        parse_mode="HTML" 
    )
    
    await state.set_state(ApplicationSteps.waiting_full_name)
    await call.message.answer("➡️ <b>1/21: Ваше полное ФИО:</b>", parse_mode="HTML") 
    await call.answer()


# 2. Телефон
@application_router.message(ApplicationSteps.waiting_full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 5:
        return await message.answer("❌ <b>Пожалуйста, введите полное ФИО (минимум 5 символов).</b>", parse_mode="HTML") 
    await state.update_data(full_name=message.text.strip())
    await state.set_state(ApplicationSteps.waiting_phone_number)
    await message.answer("📞 <b>2/21: Ваш контактный номер телефона:</b>", parse_mode="HTML") 

# 3. Email
@application_router.message(ApplicationSteps.waiting_phone_number)
async def process_phone_number(message: types.Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 5:
        return await message.answer("❌ <b>Пожалуйста, введите корректный номер телефона (минимум 5 символов).</b>", parse_mode="HTML") 
    await state.update_data(phone_number=message.text.strip())
    await state.set_state(ApplicationSteps.waiting_email)
    await message.answer("📧 <b>3/21: Ваш Email (электронная почта):</b>", parse_mode="HTML") 

@application_router.message(ApplicationSteps.waiting_email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    if not re.match(EMAIL_REGEX, email):
        return await message.answer(
            "❌ <b>Неверный формат Email.</b> Пожалуйста, введите корректный адрес (например, <code>user@example.com</code>):",
            parse_mode="HTML" 
        )
        
    await state.update_data(email=email)
    await state.set_state(ApplicationSteps.waiting_date_of_birth)
    await message.answer(
        "🗓️ <b>4/21: Ваша дата рождения (строго в формате ГГГГ-ММ-ДД, например, 2005-12-31):</b>",
        parse_mode="HTML" 
    )

# 4. Дата рождения
@application_router.message(ApplicationSteps.waiting_date_of_birth)
async def process_date_of_birth(message: types.Message, state: FSMContext):
    date_str = message.text.strip()
    
    if not re.match(DATE_REGEX, date_str):
        return await message.answer(
            "❌ <b>Неверный формат даты.</b> Пожалуйста, введите дату строго в формате <b>ГГГГ-ММ-ДД</b>:",
            parse_mode="HTML" 
        )
    
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return await message.answer(
            "❌ <b>Некорректная дата.</b> Дата не существует (например, 2025-02-30). Введите реальную дату в формате <b>ГГГГ-ММ-ДД</b>:",
            parse_mode="HTML" 
        )
        
    await state.update_data(date_of_birth=date_str)
    await state.set_state(ApplicationSteps.waiting_place_of_study)
    await message.answer(
        "🏫 <b>5/21: Место учебы (название школы/университета) и Ваш класс/курс:</b>",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML" 
    )

# 5. Место учебы
@application_router.message(ApplicationSteps.waiting_place_of_study)
async def process_place_of_study(message: types.Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 5:
        return await message.answer("❌ <b>Пожалуйста, укажите место учебы и класс/курс (минимум 5 символов).</b>", parse_mode="HTML") 
    await state.update_data(place_of_study=message.text.strip())
    await state.set_state(ApplicationSteps.waiting_photo)
    await message.answer(
        "🖼️ <b>6/21: Ваша фотография.</b>\n"
        "Пожалуйста, отправьте <b>качественное фото</b> (сжато) для анкеты.",
        parse_mode="HTML" 
    )

# 6. ФОТО
@application_router.message(F.photo, ApplicationSteps.waiting_photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo_file_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=photo_file_id)
    
    await state.set_state(ApplicationSteps.waiting_why_volunteer)
    await message.answer(
        "✅ Фото принято.\n\n"
        "💡 <b>7/21: Почему Вы хотите стать волонтером Interact club of Bishkek?</b>\n"
        "<i>(Минимум 10 символов)</i>",
        parse_mode="HTML" 
    )

@application_router.message(~F.photo, ApplicationSteps.waiting_photo)
async def process_photo_invalid(message: types.Message):
    await message.answer("❌ <b>Ошибка.</b> Пожалуйста, отправьте именно <b>фотографию</b> (не документ, не стикер).", parse_mode="HTML") 


# 7-10. Мотивация
@application_router.message(ApplicationSteps.waiting_why_volunteer)
async def process_why_volunteer(message: types.Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 10:
        return await message.answer("❌ <b>Ответ слишком короткий.</b> Пожалуйста, дайте более развернутый ответ (минимум 10 символов).", parse_mode="HTML") 
    await state.update_data(why_volunteer=message.text.strip())
    await state.set_state(ApplicationSteps.waiting_volunteer_experience)
    await message.answer(
        "📋 <b>8/21: Опыт волонтерства.</b> Расскажите, в каких сферах и организациях Вы участвовали ранее:\n"
        "<i>(Минимум 10 символов)</i>",
        parse_mode="HTML" 
    )

@application_router.message(ApplicationSteps.waiting_volunteer_experience)
async def process_volunteer_experience(message: types.Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 10:
        return await message.answer("❌ <b>Ответ слишком короткий.</b> Пожалуйста, дайте более развернутый ответ (минимум 10 символов).", parse_mode="HTML") 
    await state.update_data(volunteer_experience=message.text.strip())
    await state.set_state(ApplicationSteps.waiting_hobbies_skills)
    await message.answer(
        "🎨 <b>9/21: Ваши навыки и хобби.</b> Опишите свои увлечения, навыки, секции и организации, в которых состоите:\n"
        "<i>(Минимум 10 символов)</i>",
        parse_mode="HTML" 
    )

@application_router.message(ApplicationSteps.waiting_hobbies_skills)
async def process_hobbies_skills(message: types.Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 10:
        return await message.answer("❌ <b>Ответ слишком короткий.</b> Пожалуйста, дайте более развернутый ответ (минимум 10 символов).", parse_mode="HTML") 
    await state.update_data(hobbies_skills=message.text.strip())
    await state.set_state(ApplicationSteps.waiting_strengths)
    await message.answer(
        "💪 <b>10/21: Сильные качества.</b> Какие Ваши сильные качества помогут Вам на позиции волонтера и почему?\n"
        "<i>(Минимум 10 символов)</i>",
        parse_mode="HTML" 
    )

# 11. Выбор направлений
@application_router.message(ApplicationSteps.waiting_strengths)
async def process_strengths(message: types.Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 10:
        return await message.answer("❌ <b>Ответ слишком короткий.</b> Пожалуйста, дайте более развернутый ответ (минимум 10 символов).", parse_mode="HTML") 
    await state.update_data(strengths=message.text.strip())
    await state.set_state(ApplicationSteps.waiting_directions)
    
    # Теперь fetch_directions должен работать, если Django API доступен по 'http://backend:8000/api/'
    directions_map = await fetch_directions()
    direction_buttons = []
    
    if directions_map:
        for pk, name in directions_map.items():
            direction_buttons.append(
                [InlineKeyboardButton(text=f"{name}", callback_data=f"select_dir_{pk}")]
            )
    else:
        # Если API недоступен, даем продолжить (но логируем ошибку)
        direction_buttons.append(
            [InlineKeyboardButton(text="Направления недоступны. Продолжить ➡️", callback_data="finish_directions")]
        )
    
    direction_buttons.append(
        [InlineKeyboardButton(text="✅ Закончить выбор", callback_data="finish_directions")]
    )
    
    directions_kb = InlineKeyboardMarkup(inline_keyboard=direction_buttons)
    
    await message.answer(
        "📍 <b>11/21: Выбор направлений.</b> Пожалуйста, выберите <b>до 3 направлений</b>, в которых хотите работать. Нажимайте, чтобы выбрать/отменить.",
        reply_markup=directions_kb,
        parse_mode="HTML" 
    )
    await state.update_data(selected_directions_ids=[])

# Обработка выбора направлений
@application_router.callback_query(F.data.startswith("select_dir_"), ApplicationSteps.waiting_directions)
async def process_directions_selection(call: types.CallbackQuery, state: FSMContext):
    dir_id = int(call.data.split("_")[-1])
    data = await state.get_data()
    selected_ids = data.get('selected_directions_ids', [])
    
    direction_name = DIRECTIONS_CACHE.get(dir_id, "Неизвестное направление")

    if dir_id in selected_ids:
        selected_ids.remove(dir_id)
        action_text = f"Удалено: {direction_name}."
    else:
        if len(selected_ids) >= 3:
            return await call.answer("Лимит. Вы можете выбрать не более 3 направлений.", show_alert=True) 
        selected_ids.append(dir_id)
        action_text = f"Добавлено: {direction_name}."
    
    await state.update_data(selected_directions_ids=selected_ids)
    
    # 2. Создание новой клавиатуры с отметками
    new_buttons = []
    current_names = []
    
    # Повторное создание клавиатуры с учетом текущего выбора
    for pk, name in DIRECTIONS_CACHE.items():
        if pk in selected_ids:
            # Выбранное направление помечаем
            new_buttons.append([InlineKeyboardButton(text=f"[{name}]", callback_data=f"select_dir_{pk}")])
            current_names.append(name)
        else:
            new_buttons.append([InlineKeyboardButton(text=f"{name}", callback_data=f"select_dir_{pk}")])
            
    new_buttons.append(
        [InlineKeyboardButton(text="✅ Закончить выбор", callback_data="finish_directions")]
    )
    
    new_kb = InlineKeyboardMarkup(inline_keyboard=new_buttons)

    # 3. Редактирование сообщения
    directions_text = ", ".join(current_names) if current_names else "<i>Ничего не выбрано</i>" 
    
    try:
        await call.message.edit_text(
            f"📍 <b>11/21: Выбор направлений.</b>\n\n<b>Текущий выбор ({len(selected_ids)}):</b> {directions_text}\n\nНажмите 'Закончить выбор'.",
            reply_markup=new_kb,
            parse_mode="HTML" 
        )
    except TelegramBadRequest as e: 
        if "message is not modified" not in str(e):
            logging.warning(f"Ошибка при редактировании сообщения выбора направлений: {e}")
            pass 
        
    await call.answer(action_text)


# 12. Мотивы выбора
@application_router.callback_query(F.data == "finish_directions", ApplicationSteps.waiting_directions)
async def process_directions_finish(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_ids = data.get('selected_directions_ids', [])
    
    if not selected_ids and DIRECTIONS_CACHE:
        await call.answer("Обязательно. Пожалуйста, выберите хотя бы одно направление.", show_alert=True) 
        return
        
    await state.set_state(ApplicationSteps.waiting_choice_motives)
    
    await call.message.edit_text(
        "💬 <b>12/21: Мотивы выбора.</b> Пожалуйста, поясните, почему Вы выбрали именно эти направления:\n"
        "<i>(Минимум 10 символов)</i>",
        parse_mode="HTML" 
    )
    await call.answer("Выбор направлений завершен.")

# 13. Почему выбрать Вас?
@application_router.message(ApplicationSteps.waiting_choice_motives)
async def process_choice_motives(message: types.Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 10:
        return await message.answer("❌ <b>Ответ слишком короткий.</b> Пожалуйста, дайте более развернутый ответ (минимум 10 символов).", parse_mode="HTML") 
    await state.update_data(choice_motives=message.text.strip())
    await state.set_state(ApplicationSteps.waiting_why_choose_you)
    await message.answer(
        "✨ <b>13/21: Ваше преимущество.</b> Почему мы должны выбрать именно Вас?\n"
        "<i>(Минимум 10 символов)</i>",
        parse_mode="HTML" 
    )


# 14. Время в неделю (ВЫБОР КНОПКОЙ)
@application_router.message(ApplicationSteps.waiting_why_choose_you)
async def process_why_choose_you(message: types.Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 10:
        return await message.answer("❌ <b>Ответ слишком короткий.</b> Пожалуйста, дайте более развернутый ответ (минимум 10 символов).", parse_mode="HTML") 
    await state.update_data(why_choose_you=message.text.strip())
    
    await state.set_state(ApplicationSteps.waiting_weekly_hours) 
    
    await message.answer(
        "⏱️ <b>14/21: Время.</b> Сколько часов в неделю Вы готовы уделять клубу? Выберите подходящий интервал или введите свой вариант.", 
        reply_markup=WEEKLY_HOURS_KB,
        parse_mode="HTML" 
    )

# ОБРАБОТКА ВЫБОРА КНОПКИ ДЛЯ ВРЕМЕНИ (Шаг 14)
@application_router.callback_query(F.data.startswith("hours_"), ApplicationSteps.waiting_weekly_hours)
async def process_weekly_hours_callback(call: types.CallbackQuery, state: FSMContext):
    choice = call.data.split("_")[-1]
    
    # Обработка выбора предустановленного интервала
    if choice != "custom":
        if choice == "5":
            hours_text = "До 5 часов"
        elif choice == "5_10":
            hours_text = "5 - 10 часов"
        elif choice == "10_15":
            hours_text = "10 - 15 часов"
        elif call.data == "hours_15_plus": # <--- КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Прямая проверка полного callback_data
             hours_text = "Более 15 часов"
        else:
             hours_text = "Неизвестный интервал"

        # ПРОВЕРКА: Если все равно "Неизвестный интервал", это ошибка, прерываем.
        if hours_text == "Неизвестный интервал":
             return await call.answer("Ошибка выбора интервала. Попробуйте ввести время текстом.", show_alert=True)
            
        await state.update_data(weekly_hours=hours_text)
        await state.set_state(ApplicationSteps.waiting_attend_meetings)
        
        await call.message.edit_text(
            f"✅ 14/21: Ответ принят: <b>{hours_text}</b>.", 
            reply_markup=None, 
            parse_mode="HTML"
        )
        await call.answer(f"Вы выбрали: {hours_text}")
        
        # Переход к шагу 15
        await call.message.answer(
            "🗓️ <b>15/21: Собрания.</b> Будете ли Вы присутствовать на каждом собрании по субботам? \n(Обычно: 14:00-16:00, зависит от направления)",
            reply_markup=YES_NO_KB,
            parse_mode="HTML" 
        )
        
    # Обработка выбора "Свой вариант"
    else:
        await state.set_state(ApplicationSteps.waiting_custom_weekly_hours)
        await call.message.edit_text(
            "📝 <b>14/21: Свой вариант.</b> Пожалуйста, введите точное количество часов (или диапазон), которое Вы готовы уделять клубу в неделю:",
            reply_markup=None, 
            parse_mode="HTML"
        )
        await call.answer("Ожидаю ручной ввод.")

# ОБРАБОТКА РУЧНОГО ВВОДА ВРЕМЕНИ (Шаг 14.1)
@application_router.message(ApplicationSteps.waiting_custom_weekly_hours)
async def process_custom_weekly_hours(message: types.Message, state: FSMContext):
    custom_hours = message.text.strip()
    
    if not custom_hours or len(custom_hours) < 1:
        return await message.answer("❌ <b>Пожалуйста, введите свой вариант времени.</b>", parse_mode="HTML") 
        
    await state.update_data(weekly_hours=custom_hours)
    await state.set_state(ApplicationSteps.waiting_attend_meetings)
    
    await message.answer(
        f"✅ 14/21: Ответ принят: <b>{custom_hours}</b>.\n\n"
        "🗓️ <b>15/21: Собрания.</b> Будете ли Вы присутствовать на каждом собрании по субботам? \n(Обычно: 14:00-16:00, зависит от направления)",
        reply_markup=YES_NO_KB,
        parse_mode="HTML" 
    )


# 15. Собрания
@application_router.callback_query(F.data.in_({"answer_yes", "answer_no"}), ApplicationSteps.waiting_attend_meetings)
async def process_attend_meetings(call: types.CallbackQuery, state: FSMContext):
    answer = call.data == "answer_yes"
    await state.update_data(attend_meetings=answer)
    await state.set_state(ApplicationSteps.waiting_expectations)
    
    await call.message.edit_text(f"✅ 15/21: Ответ принят: {'Да' if answer else 'Нет'}.", reply_markup=None, parse_mode="HTML")
    
    await call.message.answer(
        "💭 <b>16/21: Ожидания.</b> Что Вы ожидаете получить от волонтерской деятельности в клубе?\n"
        "<i>(Минимум 10 символов)</i>",
        parse_mode="HTML" 
    )
    await call.answer()

# 16. Ожидания
@application_router.message(ApplicationSteps.waiting_expectations)
async def process_expectations(message: types.Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 10:
        return await message.answer("❌ <b>Ответ слишком короткий.</b> Пожалуйста, дайте более развернутый ответ (минимум 10 символов).", parse_mode="HTML") 
    await state.update_data(expectations=message.text.strip())
    await state.set_state(ApplicationSteps.waiting_ideas_improvements)
    await message.answer(
        "💡 <b>17/21: Идеи.</b> Какие идеи и нововведения Вы можете предложить для улучшения клуба?\n"
        "<i>(Минимум 10 символов)</i>",
        parse_mode="HTML" 
    )

# 17. Идеи
@application_router.message(ApplicationSteps.waiting_ideas_improvements)
async def process_ideas_improvements(message: types.Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 10:
        return await message.answer("❌ <b>Ответ слишком короткий.</b> Пожалуйста, дайте более развернутый ответ (минимум 10 символов).", parse_mode="HTML") 
    await state.update_data(ideas_improvements=message.text.strip())
    await state.set_state(ApplicationSteps.waiting_agree_inactivity_removal)
    await message.answer(
        "🚨 <b>18/21: Согласие.</b> Вы согласны, что при недостаточной активности Ваше членство может быть прекращено?",
        reply_markup=YES_NO_KB,
        parse_mode="HTML" 
    )

# 18. Согласие на удаление
@application_router.callback_query(F.data.in_({"answer_yes", "answer_no"}), ApplicationSteps.waiting_agree_inactivity_removal)
async def process_agree_inactivity_removal(call: types.CallbackQuery, state: FSMContext):
    answer = call.data == "answer_yes"
    await state.update_data(agree_inactivity_removal=answer)
    await state.set_state(ApplicationSteps.waiting_agree_terms)
    
    await call.message.edit_text(f"✅ 18/21: Ответ принят: {'Да' if answer else 'Нет'}.", reply_markup=None, parse_mode="HTML")
    await call.message.answer(
        "⚖️ <b>19/21: Условия клуба.</b> Согласны ли Вы с пунктом (!), что 'клуб под вас отвественности не берет и Ваше членство в клубе добровольное'?", 
        reply_markup=YES_NO_KB,
        parse_mode="HTML" 
    )
    await call.answer()

# 19. Соглашение с условиями ("!")
@application_router.callback_query(F.data.in_({"answer_yes", "answer_no"}), ApplicationSteps.waiting_agree_terms)
async def process_agree_terms(call: types.CallbackQuery, state: FSMContext):
    answer = call.data == "answer_yes"
    await state.update_data(agree_terms=answer)
    await state.set_state(ApplicationSteps.waiting_ready_travel)
    
    await call.message.edit_text(f"✅ 19/21: Ответ принят: {'Да' if answer else 'Нет'}.", reply_markup=None, parse_mode="HTML")
    await call.message.answer(
        "🚗 <b>20/21: Готовность к выездам.</b> Вы готовы к выездам (закуп, развоз продуктов, переговоры), даже если транспорт оплачивается не всегда?", 
        reply_markup=YES_NO_KB,
        parse_mode="HTML" 
    )
    await call.answer()

# 20. Готовность к выездам
@application_router.callback_query(F.data.in_({"answer_yes", "answer_no"}), ApplicationSteps.waiting_ready_travel)
async def process_ready_travel(call: types.CallbackQuery, state: FSMContext):
    answer = call.data == "answer_yes"
    await state.update_data(ready_travel=answer)
    
    await call.message.edit_text(f"✅ 20/21: Ответ принят: {'Да' if answer else 'Нет'}.", reply_markup=None, parse_mode="HTML")
    
    await state.set_state(ApplicationSteps.waiting_feedback)
    await call.message.answer(
        "✨ <b>21/21: Фидбэк (Отзыв).</b> Оставьте свой отзыв о процессе заполнения анкеты или любые пожелания.\n"
        "<i>(Этот шаг не обязательный. Можете сразу нажать 'Пропустить'.)</i>", 
        reply_markup=SKIP_FEEDBACK_KB,
        parse_mode="HTML" 
    )
    await call.answer()

# 21. Фидбэк и ОТПРАВКА ЧЕРЕЗ API
@application_router.callback_query(F.data == "skip_feedback", ApplicationSteps.waiting_feedback)
async def skip_feedback_and_submit(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(feedback="")
    await call.message.edit_text("⏳ <b>Заявка обрабатывается и отправляется на сервер...</b>", parse_mode="HTML") 
    await call.answer("Фидбэк пропущен.")
    await final_submit(call.message, state)
    

@application_router.message(ApplicationSteps.waiting_feedback)
async def process_feedback_and_submit(message: types.Message, state: FSMContext):
    await state.update_data(feedback=message.text.strip())
    await message.answer("⏳ <b>Заявка обрабатывается и отправляется на сервер...</b>", parse_mode="HTML") 
    await final_submit(message, state)


async def final_submit(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    # Используем обновленную функцию submit_application_to_django
    success = await submit_application_to_django(message.bot, data)
    
    if success:
        await state.clear()
        await message.answer(
            "💌 <b>Заявка принята!</b>\n\n"
            "Спасибо за Ваше время и интерес к Interact Club of Bishkek. Мы свяжемся с Вами в ближайшее время.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Ошибка отправки!</b>\n\n"
            "Не удалось отправить Вашу заявку на сервер. Пожалуйста, попробуйте еще раз позже "
            "или свяжитесь с администратором клуба.",
            parse_mode="HTML"
        )
        # Очищаем состояние только при успешной отправке
        # При ошибке, оставляем данные, чтобы пользователь мог попробовать еще раз, если потребуется.