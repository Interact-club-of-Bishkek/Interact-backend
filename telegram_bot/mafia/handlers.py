import asyncio
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from mafia.game import MafiaGame
from mafia.keyboards import join_kb, players_kb
from mafia import stats
# ИМПОРТИРУЕМ НАШЕ ХРАНИЛИЩЕ
from mafia import storage 

mafia_router = Router()

# Вспомогательная функция для редактирования сообщения по ID
async def edit_lobby_msg(bot: Bot, chat_id: int, message_id: int, text: str, reply_markup=None):
    try:
        await bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except TelegramBadRequest:
        pass # Текст не изменился
    except Exception as e:
        print(f"Ошибка редактирования: {e}")

# ---------- СТАРТ ЛОББИ ----------
@mafia_router.message(Command("start_mafia"))
async def start_lobby(msg: types.Message):
    chat_id = msg.chat.id
    
    # 1. Проверяем наличие старой игры
    if storage.load_game(chat_id):
        await msg.answer("⚠️ В этом чате уже есть активная игра.")
        return

    game = MafiaGame(chat_id)
    
    # --- ИСПРАВЛЕНИЕ ТУТ ---
    # 2. Сначала СОХРАНЯЕМ файл, чтобы он точно существовал
    print(f"[DEBUG] Создаю игру для чата {chat_id}...")
    storage.save_game(game)
    print(f"[DEBUG] Файл сохранен успешно!")
    # -----------------------

    try:
        # 3. Теперь отправляем сообщение
        sent_msg = await msg.answer(
            f"🎮 **Мафия**\n\nНажмите кнопку, чтобы войти\n"
            f"Ожидание игроков...",
            reply_markup=join_kb(),
            parse_mode="Markdown"
        )
        
        # 4. Обновляем ID сообщения в уже сохраненной игре
        game.lobby_message_id = sent_msg.message_id
        storage.save_game(game) # Сохраняем еще раз, уже с ID сообщения

        # Таймер
        asyncio.create_task(lobby_timer(msg.bot, chat_id))
        
    except Exception as e:
        # Если не удалось отправить сообщение, удаляем "мусор" из файла
        print(f"[ERROR] Ошибка отправки: {e}")
        storage.delete_game(chat_id)
        await msg.answer(f"Ошибка запуска: {e}")


async def lobby_timer(bot: Bot, chat_id: int):
    # Загружаем настройки, чтобы узнать время (сначала создадим пустышку для чтения настроек)
    # Или просто хардкодим/читаем из game, если загрузим
    game_temp = storage.load_game(chat_id)
    if not game_temp: return
    
    await asyncio.sleep(game_temp.settings["lobby_time"])
    
    # 3. ВАЖНО: Загружаем актуальное состояние из файла перед проверкой!
    # За это время второй бот мог добавить игроков в файл.
    game = storage.load_game(chat_id)
    
    if not game or not game.lobby_open:
        return

    game.lobby_open = False
    storage.save_game(game) # Закрываем лобби в файле

    if len(game.players) < game.settings["min_players"]:
        await bot.send_message(chat_id, "❌ Недостаточно игроков, лобби закрыто.")
        storage.delete_game(chat_id)
        return

    await start_game(bot, game)


# ---------- JOIN ----------
@mafia_router.callback_query(F.data == "join")
async def join_game(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    uid = str(call.from_user.id) # ID как строка
    
    # 1. Загружаем из файла
    game = storage.load_game(chat_id)

    if not game:
        await call.answer("Игра не найдена. Напишите /start_mafia", show_alert=True)
        return

    if not game.lobby_open:
        await call.answer("Лобби закрыто!", show_alert=True)
        return

    if uid in game.players:
        await call.answer("Вы уже в игре!", show_alert=True)
        return

    # 2. Меняем и сохраняем
    game.add_player(uid, call.from_user.full_name)
    storage.save_game(game)
    
    await call.answer("✅ Вы вступили!")

    # Обновляем сообщение
    players_text = "\n".join([f"• {p['name']}" for p in game.players.values()])
    text = f"🎮 **Мафия**\n\n👥 Игроки ({len(game.players)}):\n{players_text}\n\nОжидание..."
    
    await edit_lobby_msg(call.bot, chat_id, game.lobby_message_id, text, join_kb())


# ---------- СТАРТ ИГРЫ ----------
async def start_game(bot: Bot, game: MafiaGame):
    game.assign_roles()
    game.phase = "night"
    storage.save_game(game) # Сохраняем роли

    # Статистика
    for uid in game.players:
        stats.inc(uid, "games")

    # Рассылка ролей
    for uid, p in game.players.items():
        try:
            await bot.send_message(uid, f"🎭 Ваша роль: **{p['role']}**", parse_mode="Markdown")
        except: pass

    await bot.send_message(game.chat_id, f"🌙 **Ночь.** Мафия делает выбор ({game.settings['night_time']} сек).", parse_mode="Markdown")
    await night_phase(bot, game.chat_id)


# ---------- НОЧЬ ----------
async def night_phase(bot: Bot, chat_id: int):
    # Снова загружаем, чтобы убедиться в актуальности
    game = storage.load_game(chat_id)
    if not game: return

    # Очищаем голоса ночи
    game.mafia_votes = {}
    storage.save_game(game)

    mafia_ids = list(game.mafia().keys())
    if not mafia_ids:
        await asyncio.sleep(5)
        await resolve_night(bot, chat_id)
        return

    for uid in mafia_ids:
        try:
            await bot.send_message(uid, "🔫 Выберите жертву:", reply_markup=players_kb(game.alive(), "kill"))
        except: pass

    await asyncio.sleep(game.settings["night_time"])
    await resolve_night(bot, chat_id)


@mafia_router.callback_query(F.data.startswith("kill:"))
async def mafia_kill(call: types.CallbackQuery):
    uid = str(call.from_user.id)
    
    # Поиск игры (приходится перебирать файл, так как kill в ЛС)
    all_games = storage._load_db()
    target_game = None
    
    for gid, g_data in all_games.items():
        if uid in g_data.get("players", {}):
            target_game = storage.load_game(int(gid))
            break
    
    if not target_game or target_game.phase != "night":
        await call.answer("Неактуально", show_alert=True)
        await call.message.delete()
        return

    # Проверка роли
    if target_game.players[uid]['role'] not in ['mafia', 'don']:
        await call.answer("Вы не мафия", show_alert=True)
        return

    target_id = call.data.split(":")[1]
    target_game.mafia_votes[uid] = target_id
    storage.save_game(target_game) # Сохраняем голос
    
    victim = target_game.players[target_id]['name']
    await call.answer(f"Выбрано: {victim}")
    await call.message.edit_text(f"🔫 Жертва: {victim}")


# ---------- РЕЗУЛЬТАТ НОЧИ ----------
async def resolve_night(bot: Bot, chat_id: int):
    game = storage.load_game(chat_id) # Загружаем голоса
    if not game: return
    
    game.phase = "day"
    
    if game.mafia_votes:
        votes = list(game.mafia_votes.values())
        target = max(set(votes), key=votes.count)
        
        game.players[target]["alive"] = False
        stats.inc(target, "deaths")
        
        await bot.send_message(chat_id, f"☀️ Утро. **Убит:** {game.players[target]['name']}", parse_mode="Markdown")
    else:
        await bot.send_message(chat_id, "☀️ Утро. Все живы.")

    storage.save_game(game)
    await day_phase(bot, chat_id)


# ---------- ДЕНЬ ----------
async def day_phase(bot: Bot, chat_id: int):
    game = storage.load_game(chat_id)
    if await check_end_game(bot, game): return

    game.phase = "vote"
    game.vote_votes = {}
    storage.save_game(game)

    await bot.send_message(chat_id, "🗳 **Голосование!** Ищите мафию.", reply_markup=players_kb(game.alive(), "vote"), parse_mode="Markdown")
    
    await asyncio.sleep(game.settings["vote_time"])
    await resolve_vote(bot, chat_id)


@mafia_router.callback_query(F.data.startswith("vote:"))
async def vote_handler(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    uid = str(call.from_user.id)
    
    game = storage.load_game(chat_id)
    if not game: return # Если игра удалена

    if game.phase != "vote":
        await call.answer("Голосование закрыто", show_alert=True)
        return

    if uid not in game.players or not game.players[uid]["alive"]:
        await call.answer("Вы не можете голосовать", show_alert=True)
        return

    target = call.data.split(":")[1]
    game.vote_votes[uid] = target
    storage.save_game(game) # Сохраняем голос
    
    await call.answer("Голос принят")


async def resolve_vote(bot: Bot, chat_id: int):
    game = storage.load_game(chat_id) # Считываем голоса из файла
    if not game: return

    if not game.vote_votes:
        await bot.send_message(chat_id, "🤷‍♂️ Никто не голосовал.")
    else:
        counts = {}
        for t in game.vote_votes.values(): counts[t] = counts.get(t, 0) + 1
        top = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        
        if len(top) > 1 and top[0][1] == top[1][1]:
            await bot.send_message(chat_id, "⚖️ Ничья.")
        else:
            victim_id = top[0][0]
            game.players[victim_id]["alive"] = False
            stats.inc(victim_id, "deaths")
            await bot.send_message(chat_id, f"❌ Линчеван: {game.players[victim_id]['name']}")

    game.phase = "night"
    storage.save_game(game)
    
    if await check_end_game(bot, game): return
    
    await bot.send_message(chat_id, "🌙 Город засыпает...")
    await night_phase(bot, chat_id)


async def check_end_game(bot: Bot, game: MafiaGame) -> bool:
    winner = game.check_winner()
    if winner:
        txt = "🔫 Победа Мафии!" if winner == "mafia" else "🕊 Победа Мирных!"
        await bot.send_message(game.chat_id, f"🏁 {txt}")
        
        # Начисляем победы
        mafia_roles = ["mafia", "don"]
        for uid, p in game.players.items():
            is_mafia = p['role'] in mafia_roles
            if (winner == "mafia" and is_mafia) or (winner == "civilian" and not is_mafia):
                stats.inc(uid, "wins")
        
        storage.delete_game(game.chat_id)
        return True
    return False