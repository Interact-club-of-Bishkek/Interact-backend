# general/handlers.py
from aiogram import Router, types, F
from aiogram.filters import Command

general_router = Router()

# Кнопки для приветственного сообщения
def start_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        [
            types.InlineKeyboardButton(
                text="🌟 Оставить заявку стать волонтером", 
                callback_data="volunteer_apply"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="🧠 ИИ Ассистент Interact Club", 
                callback_data="ai_assistant"
            )
        ],
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)


@general_router.message(Command("start"), F.chat.type == "private")
async def handle_private_start(msg: types.Message):
    """Обрабатывает команду /start ТОЛЬКО в личных сообщениях с улучшенным текстом."""
    
    welcome_text = (
        "✨ **Добро пожаловать в Interact Club of Bishkek!** ✨\n\n"
        "Мы — международная благотворительная организация, объединяющая активную "
        "молодежь Бишкека для реализации социальных проектов и создания позитивных перемен.\n\n"
        "🤝 **Наша миссия:** Развивать лидерские качества, помогать обществу и строить дружеские связи.\n\n"
        "Выберите действие, чтобы узнать больше или начать свой путь с нами:"
    )
    
    await msg.answer(
        welcome_text,
        reply_markup=start_keyboard(),
        parse_mode="Markdown"
    )

@general_router.callback_query(F.data.in_({"volunteer_apply", "ai_assistant"}))
async def handle_under_development(call: types.CallbackQuery):
    """Обрабатывает нажатие кнопок 'В разработке'."""
    await call.answer("🛠 Функция находится в разработке. Скоро вернемся с обновлениями!", show_alert=True)