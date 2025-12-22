import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Optional

# ❗ ИМПОРТ КНОПКИ ИГРЫ КРОКОДИЛ
try:
    from crocodile.crocodile_runner import kb_play_croc 
except ImportError:
    def kb_play_croc():
        return types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🐊 Играть в Крокодила", callback_data="start_croc_game")]
        ])

# --- ИМПОРТ ИИ (оставляем импорт, если файл существует, но не используем вызовы) ---
try:
    from ai_command.ai_service import ai_bot 
except ImportError:
    ai_bot = None

general_router = Router()

class AIState(StatesGroup):
    waiting_for_question = State()

# ---------- КЛАВИАТУРЫ И ТЕКСТЫ ----------
def club_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        [types.InlineKeyboardButton(text="🌟 Оставить заявку стать волонтером", callback_data="volunteer_apply")],
        [types.InlineKeyboardButton(text="🧠 ИИ Ассистент Interact Club", callback_data="ai_assistant")],
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def stop_ai_keyboard() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="❌ Закончить диалог")]],
        resize_keyboard=True
    )

def game_keyboard() -> types.InlineKeyboardMarkup:
    croc_button: types.InlineKeyboardButton = kb_play_croc().inline_keyboard[0][0]
    mafia_button = types.InlineKeyboardButton(text="🔫 Играть в Мафию", callback_data="start_mafia_game")
    return types.InlineKeyboardMarkup(inline_keyboard=[[croc_button], [mafia_button]])

def get_welcome_text(user_name: Optional[str]) -> str:
    name = f", {user_name}" if user_name else ""
    
    return (
        f"✨ <b>Добро пожаловать в Interact Club of Bishkek{name}!</b>\n\n"
        
        f"<b>Interact Club of Bishkek</b> — это официальное молодежное подразделение "
        f"<b>Rotary International</b>, основанное в 2012 году. "
        f"Мы являемся первым и одним из самых активных Interact-клубов в Кыргызстане "
        f"и объединяем молодых людей в возрасте от 14 до 19 лет, "
        f"которые хотят развиваться, брать ответственность и менять общество к лучшему. 🌍🇰🇬\n\n"
        
        f"<b>Наша миссия</b>\n"
        f"Мы верим в принцип <b>Service Above Self</b> — служение обществу выше личных интересов. "
        f"Через волонтерство, лидерство и командную работу мы формируем новое поколение "
        f"инициативных и социально ответственных лидеров.\n\n"
        
        f"<b>Чем занимается клуб?</b>\n"
        f"📌 <b>Социальные проекты:</b> помощь детским домам, пожилым людям, ветеранам, "
        f"проведение благотворительных сборов и акций.\n"
        f"📌 <b>Экологические инициативы:</b> субботники, эко-кампании, проекты по осознанному потреблению.\n"
        f"📌 <b>Образовательные ивенты:</b> тренинги, воркшопы, встречи со спикерами, "
        f"развитие soft skills и лидерских качеств.\n"
        f"📌 <b>Городские и культурные мероприятия:</b> участие в общественной жизни города и страны.\n\n"
        
        f"<b>Международные возможности</b>\n"
        f"Interact — часть глобальной семьи Rotary, включающей десятки тысяч клубов по всему миру. "
        f"Участники получают доступ к международным форумам, совместным проектам, "
        f"онлайн-мероприятиям и программам обмена.\n\n"
        
        f"<b>Что дает участие в Interact?</b>\n"
        f"✔ Реальный опыт командной и проектной работы\n"
        f"✔ Развитие лидерства и ответственности\n"
        f"✔ Новые знакомства и сильное комьюнити\n"
        f"✔ Портфолио проектов и волонтерских часов\n"
        f"✔ Подготовку к Rotaract и Rotary в будущем 🚀\n\n"
        
        f"<b>Зачем нужен этот бот?</b>\n"
        f"• Подать заявку на вступление в клуб 🙋‍♂️\n"
        f"• Узнавать о текущих проектах и мероприятиях 📅\n"
        f"• Быть на связи с клубом и его активностями\n"
        f"• Взаимодействовать с комьюнити в удобном формате 🎮\n\n"
        
        f"💻 <b>О разработке</b>\n"
        f"Бот разработан <b>IT-отделом Interact Club of Bishkek</b> "
        f"как часть цифровой экосистемы клуба. "
        f"Наша цель — сделать участие в клубе максимально прозрачным, "
        f"удобным и современным для каждого участника.\n\n"
        
        f"<i>Присоединяйся к движению и выбери нужный раздел ниже!</i> 👇"
    )


# ---------- ХЕНДЛЕРЫ КОМАНД ----------

@general_router.message(Command("start"), F.chat.type == ChatType.PRIVATE, StateFilter(None))
async def handle_private_start(msg: types.Message, state: FSMContext):
    await state.clear()
    user_name = msg.from_user.first_name if msg.from_user else "друг"
    await msg.answer(get_welcome_text(user_name), reply_markup=club_keyboard(), parse_mode="HTML")

# ---------- ХЕНДЛЕРЫ ИИ (В РАЗРАБОТКЕ) ----------

@general_router.callback_query(F.data == "ai_assistant") 
async def ai_in_development_menu(call: types.CallbackQuery):
    """Редактирует сообщение, показывая статус разработки и кнопку возврата."""
    
    # Создаем кнопку назад
    kb_back = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main")]
    ])
    
    await call.message.edit_text(
        "🤖 <b>ИИ Ассистент Interact Club</b>\n\n"
        "🛠 К сожалению, данный раздел сейчас находится в <b>разработке</b>.\n"
        "Мы наполняем базу знаний, чтобы ответы были максимально полезными.\n\n"
        "<i>Пожалуйста, возвращайтесь позже!</i>",
        reply_markup=kb_back,
        parse_mode="HTML"
    )
    await call.answer()

@general_router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(call: types.CallbackQuery):
    """Возвращает пользователя к основному приветствию."""
    user_name = call.from_user.first_name if call.from_user else "друг"
    
    await call.message.edit_text(
        get_welcome_text(user_name),
        reply_markup=club_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()
@general_router.message(Command("train_ai"))
async def admin_train_ai(msg: types.Message):
    await msg.answer("🛠 Функция индексации временно недоступна.")

@general_router.message(Command("train_ai"))
async def admin_train_ai(msg: types.Message):
    await msg.answer("🛠 Функция индексации временно отключена, так как модуль находится на техобслуживании.")