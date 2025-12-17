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

# --- ИМПОРТ ИИ ---
from ai_command.ai_service import ai_bot 

general_router = Router()

# --- FSM: Состояния для ИИ ---
class AIState(StatesGroup):
    waiting_for_question = State()

# Максимальный лимит символов для Telegram сообщения
MAX_TELEGRAM_MESSAGE_LENGTH = 4000

# Функция для разделения текста
def split_text_into_chunks(text: str, max_len: int) -> list[str]:
    """Разделяет длинный текст на части, стараясь сохранить целостность предложений."""
    if len(text) <= max_len:
        return [text]
    
    chunks = []
    current_chunk = ""
    sentences = text.split('\n')
    
    for sentence in sentences:
        if len(sentence) > max_len:
            for i in range(0, len(sentence), max_len):
                chunks.append(sentence[i:i + max_len])
            continue

        if len(current_chunk) + len(sentence) + 1 > max_len:
            chunks.append(current_chunk)
            current_chunk = sentence + "\n"
        else:
            current_chunk += sentence + "\n"

    if current_chunk:
        chunks.append(current_chunk)

    return [chunk.strip() for chunk in chunks if chunk.strip()]


# ---------- КЛАВИАТУРЫ И ТЕКСТЫ (без изменений) ----------
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
    user_greeting = f"✨ <b>Добро пожаловать, {user_name}!</b> ✨\n\n" if user_name else "✨ <b>Добро пожаловать в Interact Club of Bishkek!</b> ✨\n\n"
    return (f"{user_greeting}"
            "Мы — международная благотворительная организация.\n\n"
            "🤝 <b>Наша миссия:</b> Развивать лидерские качества.\n\n"
            "Выберите действие:")

def get_group_start_text() -> str:
    return "🎮 <b>Начнём игру!</b>\nВыберите игру."

# ---------- ХЕНДЛЕРЫ КОМАНД ----------

@general_router.message(Command("start"), F.chat.type == ChatType.PRIVATE, StateFilter(None))
async def handle_private_start(msg: types.Message, state: FSMContext):
    await state.clear()
    user_name = msg.from_user.first_name if msg.from_user else "друг"
    await msg.answer(get_welcome_text(user_name), reply_markup=club_keyboard(), parse_mode="HTML")

@general_router.message(Command("start"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def handle_group_start(msg: types.Message):
    await msg.answer(get_group_start_text(), reply_markup=game_keyboard(), parse_mode="HTML")

# ---------- ХЕНДЛЕРЫ ИИ (AI) ----------

@general_router.callback_query(F.data == "ai_assistant") 
async def start_ai_dialog(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(AIState.waiting_for_question)
    
    await call.message.answer(
        "🤖 <b>Я ИИ-ассистент Interact Club.</b>\n\n"
        "Я изучил документы организации и готов ответить на ваши вопросы.\n\n"
        "<i>Напишите ваш вопрос ниже:</i>",
        reply_markup=stop_ai_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@general_router.message(F.text == "❌ Закончить диалог", StateFilter(AIState.waiting_for_question))
async def stop_ai_dialog(msg: types.Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "Диалог с ИИ завершен. Возвращаю главное меню.", 
        reply_markup=types.ReplyKeyboardRemove()
    )
    await msg.answer(get_welcome_text(msg.from_user.first_name), reply_markup=club_keyboard(), parse_mode="HTML")

@general_router.message(F.text, StateFilter(AIState.waiting_for_question))
async def process_ai_question(msg: types.Message):
    await msg.bot.send_chat_action(chat_id=msg.chat.id, action="typing")
    
    try:
        full_answer = await ai_bot.get_answer(msg.text)
        
        answer_chunks = split_text_into_chunks(full_answer, MAX_TELEGRAM_MESSAGE_LENGTH)
        
        if not answer_chunks:
             await msg.answer("Извините, ответ не удалось сформировать.")
             return
             
        for chunk in answer_chunks:
            await msg.answer(chunk, parse_mode="HTML") 
            await asyncio.sleep(0.5) 
            
    except Exception as e:
        await msg.answer(f"Произошла ошибка при генерации ответа: {e}")

@general_router.message(Command("train_ai"))
async def admin_train_ai(msg: types.Message):
    await msg.answer("⏳ **Запускаю индексацию базы знаний...** Это может занять несколько секунд.", parse_mode="HTML")
    
    try:
        # !!! Используем asyncio.to_thread для запуска синхронной функции build_index !!!
        status = await asyncio.to_thread(ai_bot.build_index)
        await msg.answer(f"✅ **Индексация завершена!**\n\n{status}", parse_mode="HTML")
    except Exception as e:
        await msg.answer(f"❌ **Критическая ошибка при индексации:**\n{e}", parse_mode="HTML")