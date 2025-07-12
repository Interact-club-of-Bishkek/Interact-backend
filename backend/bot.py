import os
import django
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from django.core.files.base import ContentFile
from asgiref.sync import sync_to_async
from asgiref.sync import async_to_sync

# Инициализация Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "interact.settings")
django.setup()

from form.models import VolunteerForm
from users.models import Volunteer

BOT_TOKEN = "7812750597:AAFGYMnhgpeU09w6ZzajzpxbYRQX3iIvQdY"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# FSM состояния регистрации
class FormStates(StatesGroup):
    name = State()
    phone_number = State()
    image = State()
    telegram_username = State()


@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await message.answer("Привет! Давайте начнем регистрацию. Введите ваше ФИО:")
    await state.set_state(FormStates.name)


@dp.message(FormStates.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите номер телефона:")
    await state.set_state(FormStates.phone_number)


@dp.message(FormStates.phone_number)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone_number=message.text)
    await message.answer("Отправьте фотографию:")
    await state.set_state(FormStates.image)


@dp.message(FormStates.image, F.photo)
async def get_image(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    content = await bot.download_file(file.file_path)
    await state.update_data(image=ContentFile(content.read(), name=f"{photo.file_id}.jpg"))
    await message.answer("Введите ваш Telegram @username (без @):")
    await state.set_state(FormStates.telegram_username)


@dp.message(FormStates.telegram_username)
async def get_username(message: types.Message, state: FSMContext):
    data = await state.get_data()
    username = message.text.strip()
    tg_id = message.from_user.id

    await sync_to_async(VolunteerForm.objects.create)(
        name=data['name'],
        phone_number=data['phone_number'],
        image=data['image'],
        telegram_username=username,
        telegram_id=tg_id,
    )

    await message.answer("Спасибо! Ваша заявка отправлена на проверку ✅")
    await state.clear()


async def send_account_data_to_users():
    volunteers = await sync_to_async(list)(
        Volunteer.objects.exclude(telegram_id__isnull=True).exclude(telegram_id=0)
    )

    for volunteer in volunteers:
        try:
            msg = (
                f"👋 Привет, {volunteer.name}!\n\n"
                f"Вот твои данные для входа:\n"
                f"Логин: <code>{volunteer.login}</code>\n"
                f"Пароль: <code>{volunteer.visible_password}</code>"
            )
            await bot.send_message(chat_id=volunteer.telegram_id, text=msg, parse_mode="HTML")
        except Exception as e:
            print(f"❌ Ошибка отправки {volunteer.name} ({volunteer.telegram_id}): {e}")

async def send_single_message(user_id: int, message: str):
    try:
        await bot.send_message(chat_id=user_id, text=message)
    except Exception as e:
        print(f"Ошибка при отправке сообщения {user_id}: {e}")
        
async def send_text_to_user(telegram_id: int, text: str):
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(chat_id=telegram_id, text=text, parse_mode=ParseMode.HTML)
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения пользователю {telegram_id}: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(dp.start_polling(bot))
