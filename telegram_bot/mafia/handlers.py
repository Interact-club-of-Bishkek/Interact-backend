import asyncio
import html
from collections import Counter
from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError 

from mafia.game import MafiaGame, MAFIA_TEAM, ROLE_NAMES
from mafia import storage, stats
# Предполагаем, что join_kb(is_creator) возвращает кнопку "Начать сейчас", если is_creator=True
from mafia.keyboards import join_kb, settings_kb, players_kb, sheriff_choice_kb

mafia_router = Router()

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------

def generate_lobby_text(game: MafiaGame) -> str:
    """Генерирует кликабельный список игроков в HTML с учетом создателя."""
    players_lines = []
    
    if not game.players:
        players_text = "<i>Пока никого нет...</i>"
    else:
        for uid, p in game.players.items():
            safe_name = html.escape(p['name'])
            is_creator = str(game.creator_id) == uid
            
            link = f'<a href="tg://user?id={uid}">{safe_name}</a>'
            players_lines.append(f"• {link}" + (" 👑" if is_creator else ""))
        players_text = "\n".join(players_lines)

    return (
        f"🎮 <b>Мафия</b>\n\n"
        f"👥 Игроки ({len(game.players)}):\n"
        f"{players_text}\n\n"
        f"⏳ <i>Нажмите кнопку, чтобы вступить.</i>"
    )

# ---------- СТАРТ ИГРЫ (ЛОББИ) ----------
@mafia_router.message(Command("start_mafia"), F.chat.type.in_({"group", "supergroup"}))
async def start_lobby(msg: types.Message):
    chat_id = msg.chat.id
    creator_id = str(msg.from_user.id)
    
    if storage.load_game(chat_id):
        await msg.answer("⚠️ В этом чате уже есть активная игра.")
        return

    game = MafiaGame(chat_id)
    game.add_player(creator_id, msg.from_user.full_name) 
    game.creator_id = creator_id
    storage.save_game(game)

    text = generate_lobby_text(game)

    # При создании лобби is_creator = True
    sent_msg = await msg.answer(
        text,
        reply_markup=join_kb(is_creator=True), 
        parse_mode="HTML"
    )
    game.lobby_message_id = sent_msg.message_id
    storage.save_game(game)
    asyncio.create_task(lobby_cycle(msg.bot, chat_id))

# ---------- НОВАЯ КОМАНДА: ОТМЕНА ЛОББИ ----------
@mafia_router.message(Command("cancel_mafia"), F.chat.type.in_({"group", "supergroup"}))
async def cancel_lobby(msg: types.Message):
    chat_id = msg.chat.id
    uid = str(msg.from_user.id)
    game = storage.load_game(chat_id)

    if not game:
        return await msg.answer("Нет активного лобби или игры для отмены.")

    # Проверка, находится ли игра в стадии лобби
    if not game.lobby_open:
        return await msg.answer("Игра уже началась. Используйте команду /stop_mafia для принудительной остановки.")

    # Проверка прав: только создатель может отменить лобби
    if game.creator_id != uid:
        return await msg.answer("❌ Только создатель игры (которому принадлежит 👑) может отменить лобби.")

    # Удаляем игру из хранилища
    storage.delete_game(chat_id)

    # Попытка удалить сообщение лобби
    try:
        await msg.bot.delete_message(chat_id, game.lobby_message_id)
    except Exception:
        # Игнорируем ошибку, если сообщение уже удалено или не найдено
        pass

    await msg.answer("🛑 Лобби отменено. Вы можете начать новую игру командой /start_mafia.")


# ---------- ОСТАНОВКА ИГРЫ (принудительная, включая начатую) ----------
@mafia_router.message(Command("stop_mafia"), F.chat.type.in_({"group", "supergroup"}))
async def stop_mafia(msg: types.Message):
    chat_id = msg.chat.id
    game = storage.load_game(chat_id)
    
    if not game:
        return await msg.answer("Нет активной игры для остановки.")
    
    # Можно добавить проверку прав администратора или создателя, но для простоты оставляем только удаление
    
    storage.delete_game(chat_id)
    
    if game.lobby_open:
        try:
            await msg.bot.delete_message(chat_id, game.lobby_message_id)
        except Exception:
            pass # Игнорируем, если не удалось удалить старое лобби
        await msg.answer("✅ Лобби остановлено и удалено из хранилища.")
    else:
        await msg.answer("⚠️ Игра была принудительно остановлена. Данные удалены.")


async def lobby_cycle(bot: Bot, chat_id: int):
    """Цикл ожидания лобби"""
    game = storage.load_game(chat_id)
    if not game: return
    
    await asyncio.sleep(game.settings["lobby_time"])
    
    game = storage.load_game(chat_id)
    if not game or not game.lobby_open: return

    game.lobby_open = False
    storage.save_game(game)

    if len(game.players) < game.settings["min_players"]:
        await bot.send_message(chat_id, "❌ Недостаточно игроков. Игра отменена.")
        storage.delete_game(chat_id)
        return

    await start_game_logic(bot, game)

@mafia_router.callback_query(F.data == "join")
async def join_game(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    uid = str(call.from_user.id)
    game = storage.load_game(chat_id)

    if not game or not game.lobby_open:
        await call.answer("Лобби закрыто", show_alert=True)
        return
    if uid in game.players:
        await call.answer("Вы уже в игре", show_alert=True)
        return

    game.add_player(uid, call.from_user.full_name)
    storage.save_game(game)
    
    # ❗️ ИСПРАВЛЕНИЕ: Всегда передаем is_creator=True, чтобы кнопка "Начать сейчас" оставалась видимой
    
    text = generate_lobby_text(game)

    try:
        await call.message.edit_text(text, reply_markup=join_kb(is_creator=True), parse_mode="HTML")
    except TelegramBadRequest: 
        pass 
    
    await call.answer("✅ Вы вступили")
    
# ---------- МГНОВЕННЫЙ СТАРТ ----------
@mafia_router.callback_query(F.data == "start_now")
async def instant_start_game(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    uid = str(call.from_user.id)
    game = storage.load_game(chat_id)

    if not game or not game.lobby_open:
        return await call.answer("Лобби закрыто.")
    
    # ⚠️ Эта проверка гарантирует, что только создатель может нажать кнопку.
    if str(game.creator_id) != uid:
        return await call.answer("❌ Только создатель игры может начать досрочно!", show_alert=True)

    if len(game.players) < game.settings["min_players"]:
        return await call.answer(f"❌ Нельзя начать! Минимум {game.settings['min_players']} игрока.", show_alert=True)

    game.lobby_open = False
    storage.save_game(game)
    
    await call.message.edit_text(
        f"🚀 Создатель <b>{call.from_user.full_name}</b> начал игру досрочно!",
        reply_markup=None,
        parse_mode="HTML"
    )
    
    await call.answer("Игра начинается!")
    
    await start_game_logic(call.bot, game)


async def start_game_logic(bot: Bot, game: MafiaGame):
    game.assign_roles()
    storage.save_game(game)

    for uid, p in game.players.items():
        stats.inc(uid, "games")
        role_name = ROLE_NAMES.get(p["role"], p["role"])
        try:
            await bot.send_message(uid, f"🎭 Ваша роль: <b>{role_name}</b>", parse_mode="HTML")
        except TelegramForbiddenError:
            print(f"Игрок {uid} не запустил бота и не получит роль в ЛС.")
        except Exception: 
            pass

    await bot.send_message(game.chat_id, "🏙 <b>Город засыпает... Наступает ночь.</b>", parse_mode="HTML")
    await night_phase(bot, game.chat_id)

# ---------- НОЧЬ ----------
async def night_phase(bot: Bot, chat_id: int):
    game = storage.load_game(chat_id)
    if not game: return

    game.phase = "night"
    game.mafia_votes = {}
    game.doctor_target = None
    game.sheriff_target = None
    game.sheriff_action_type = None
    game.night_messages = []
    storage.save_game(game)

    status_msg = []

    for uid, p in game.players.items():
        if not p["alive"]: continue
        
        targets = {k:v for k,v in game.alive().items() if k != uid}

        try:
            # МАФИЯ
            if p["role"] in MAFIA_TEAM:
                msg = await bot.send_message(
                    uid, 
                    "🔫 <b>Мафия</b>, выберите жертву.\n🗣 Вы можете общаться здесь — сообщения увидят другие мафиози.", 
                    reply_markup=players_kb(targets, chat_id, exclude=uid, action="kill"),
                    parse_mode="HTML"
                )
                game.night_messages.append(msg.message_id)
            
            # ДОКТОР
            elif p["role"] == "doctor":
                status_msg.append("👨‍⚕️ Доктор вышел на дежурство...")
                msg = await bot.send_message(
                    uid, 
                    "🩺 <b>Доктор</b>, кого будем лечить?", 
                    reply_markup=players_kb(game.alive(), chat_id, action="heal"),
                    parse_mode="HTML"
                )
                game.night_messages.append(msg.message_id)
            
            # ШЕРИФ
            elif p["role"] == "sheriff":
                status_msg.append("👮 Шериф патрулирует улицы...")
                msg = await bot.send_message(
                    uid, 
                    "🕵️ <b>Шериф</b>, выберите действие:", 
                    reply_markup=sheriff_choice_kb(chat_id),
                    parse_mode="HTML"
                )
                game.night_messages.append(msg.message_id)
        
        except TelegramForbiddenError:
            pass
        except Exception as e:
            print(f"Ошибка при отправке ночного меню игроку {uid}: {e}")

    if status_msg:
        await bot.send_message(chat_id, "\n".join(set(status_msg)))
    
    storage.save_game(game)
    
    await asyncio.sleep(game.settings["night_time"])
    await resolve_night(bot, chat_id)

# ---------- ДЕЙСТВИЯ НОЧЬЮ (CALLBACKS) ----------

@mafia_router.callback_query(F.data.startswith("sh_choice:"))
async def sheriff_choose_mode(call: types.CallbackQuery):
    _, mode, chat_id = call.data.split(":")
    chat_id = int(chat_id)
    game = storage.load_game(chat_id)
    
    if str(call.from_user.id) not in game.players or game.players[str(call.from_user.id)]["role"] != "sheriff":
        return await call.answer("Вы не шериф!")

    game.sheriff_action_type = mode
    storage.save_game(game)

    action_verb = "проверить" if mode == "check" else "застрелить"
    targets = {k:v for k,v in game.alive().items() if k != str(call.from_user.id)}
    
    await call.message.edit_text(
        f"🕵️ Выберите игрока, которого хотите <b>{action_verb}</b>:", 
        reply_markup=players_kb(targets, chat_id, exclude=str(call.from_user.id), action="sheriff_act"),
        parse_mode="HTML"
    )
    await call.answer()

@mafia_router.callback_query(F.data.startswith("sheriff_act:"))
async def sheriff_act_target(call: types.CallbackQuery):
    _, chat_id, target_id = call.data.split(":")
    chat_id = int(chat_id)
    game = storage.load_game(chat_id)
    
    if not game.sheriff_action_type:
        return await call.answer("Сначала выберите действие!")

    game.sheriff_target = target_id
    storage.save_game(game)
    
    target_name = game.players[target_id]["name"]
    
    if game.sheriff_action_type == "check":
        role = game.players[target_id]["role"]
        is_mafia = role in MAFIA_TEAM
        res_text = "🕵️ Это <b>МАФИЯ</b>!" if is_mafia else "👤 Это мирный гражданин."
        await call.message.edit_text(f"Вы проверили {target_name}.\n{res_text}", parse_mode="HTML")
    else:
        await call.message.edit_text(f"Вы решили застрелить {target_name}. Ждем утра.", parse_mode="HTML")
    await call.answer("Выбор сделан")

@mafia_router.callback_query(F.data.startswith("kill:"))
async def mafia_vote(call: types.CallbackQuery):
    _, chat_id, target_id = call.data.split(":")
    chat_id = int(chat_id)
    uid = str(call.from_user.id)
    game = storage.load_game(chat_id)
    
    game.mafia_votes[uid] = target_id
    storage.save_game(game)
    
    target_name = game.players[target_id]["name"]
    
    team = [u for u, p in game.players.items() if p["role"] in MAFIA_TEAM and p["alive"]]
    for mid in team:
        if mid != uid:
            try:
                await call.bot.send_message(mid, f"🔫 Тиммейт проголосовал за: <b>{target_name}</b>", parse_mode="HTML")
            except TelegramForbiddenError:
                pass
            except Exception: pass
            
    await call.answer(f"Голос за {target_name} принят")
    try:
        await call.message.edit_text(f"Ваш голос: <b>{target_name}</b>", parse_mode="HTML")
    except TelegramBadRequest: pass

@mafia_router.callback_query(F.data.startswith("heal:"))
async def doctor_heal(call: types.CallbackQuery):
    _, chat_id, target_id = call.data.split(":")
    chat_id = int(chat_id)
    game = storage.load_game(chat_id)
    
    game.doctor_target = target_id
    storage.save_game(game)
    
    await call.message.edit_text(f"Вы решили лечить: <b>{game.players[target_id]['name']}</b>", parse_mode="HTML")
    await call.answer("Выбор сделан")

# ---------- РАЗРЕШЕНИЕ НОЧИ ----------
async def resolve_night(bot: Bot, chat_id: int):
    game = storage.load_game(chat_id)
    if not game: return
    
    # Удаляем сообщения ночи
    for mid in game.night_messages:
        try: await bot.delete_message(chat_id=chat_id, message_id=mid)
        except: pass

    dead_players = []

    # 1. Расчет выстрела мафии
    mafia_target = None
    if game.mafia_votes:
        votes = list(game.mafia_votes.values())
        mafia_target = Counter(votes).most_common(1)[0][0]

    if mafia_target and mafia_target != game.doctor_target:
        dead_players.append(mafia_target)

    # 2. Расчет выстрела шерифа (если он выбрал убить)
    if game.sheriff_action_type == "kill" and game.sheriff_target:
        if game.sheriff_target != game.doctor_target:
            if game.sheriff_target not in dead_players:
                dead_players.append(game.sheriff_target)

    # Применяем смерти
    result_text = "🌅 <b>Наступило утро.</b>\n"
    
    if not dead_players:
        result_text += "Ночь прошла спокойно. Никто не умер."
    else:
        for uid in set(dead_players):
            # НОВОЕ: Разрешаем одно "последнее слово"
            game.players[uid]["last_word_allowed"] = True 
            game.players[uid]["alive"] = False
            
            result_text += f"💀 Был убит: <b>{game.players[uid]['name']}</b> ({ROLE_NAMES[game.players[uid]['role']]})\n"
            stats.inc(uid, "games")

    storage.save_game(game)
    await bot.send_message(chat_id, result_text, parse_mode="HTML")
    
    if await check_end_game(bot, game): return
    
    await day_phase(bot, chat_id)

# ---------- ДЕНЬ (ГОЛОСОВАНИЕ) ----------
async def day_phase(bot: Bot, chat_id: int):
    game = storage.load_game(chat_id)
    
    game.phase = "vote"
    game.vote_votes = {}
    storage.save_game(game)
    
    await bot.send_message(chat_id, "🗣 Объявляется дневное обсуждение! У вас есть время, чтобы вычислить мафию.")
    
    await bot.send_message(chat_id, f"🗳 <b>Голосование началось!</b> ({game.settings['vote_time']} сек)", parse_mode="HTML")
    
    for uid in game.alive():
        targets = {k:v for k,v in game.alive().items() if k != uid}
        try:
            await bot.send_message(uid, "Кого вы хотите посадить в тюрьму?", reply_markup=players_kb(targets, chat_id, exclude=uid, action="vote"))
        except TelegramForbiddenError:
             pass
        except Exception: 
            pass

    await asyncio.sleep(game.settings["vote_time"])
    await resolve_vote(bot, chat_id)

@mafia_router.callback_query(F.data.startswith("vote:"))
async def vote_handler(call: types.CallbackQuery):
    _, chat_id, target_id = call.data.split(":")
    chat_id = int(chat_id)
    uid = str(call.from_user.id)
    
    game = storage.load_game(chat_id)
    if game.phase != "vote":
        return await call.answer("Голосование окончено")
    
    game.vote_votes[uid] = target_id
    storage.save_game(game)
    
    target_name = game.players[target_id]["name"]
    await call.answer(f"Вы проголосовали за {target_name}")
    try:
        await call.message.edit_text(f"Ваш голос: <b>{target_name}</b>", parse_mode="HTML")
    except: pass

async def resolve_vote(bot: Bot, chat_id: int):
    game = storage.load_game(chat_id)
    if not game: return
    
    await bot.send_message(chat_id, "🗳 Голосование завершено. Подсчитываем голоса...")
    
    if not game.vote_votes:
        await bot.send_message(chat_id, "🤷‍♂️ Никто не голосовал. Никто не выгнан.")
    else:
        counter = Counter(game.vote_votes.values())
        most_common = counter.most_common(2)
        
        if len(most_common) > 1 and most_common[0][1] == most_common[1][1]:
            await bot.send_message(chat_id, "⚖️ Ничья по голосам. Никто не выгнан.")
        else:
            kicked_id = most_common[0][0]
            kicked_player = game.players[kicked_id]
            
            # НОВОЕ: Разрешаем одно "последнее слово"
            game.players[kicked_id]["last_word_allowed"] = True 
            game.players[kicked_id]["alive"] = False
            storage.save_game(game)
            
            await bot.send_message(
                chat_id, 
                f"⚖️ Решением города был изгнан: <b>{kicked_player['name']}</b>\nЕго роль: <b>{ROLE_NAMES[kicked_player['role']]}</b>",
                parse_mode="HTML"
            )

    if await check_end_game(bot, game): return
    
    await bot.send_message(chat_id, "🏙 Город засыпает...")
    await night_phase(bot, chat_id)

# ---------- КОНЕЦ ИГРЫ (РАСКРЫТИЕ РОЛЕЙ) ----------
async def check_end_game(bot: Bot, game: MafiaGame) -> bool:
    alive = list(game.alive().values())
    mafia_count = sum(1 for p in alive if p["role"] in MAFIA_TEAM)
    civil_count = sum(1 for p in alive if p["role"] not in MAFIA_TEAM)

    winner = None
    if mafia_count == 0:
        winner = "civilian"
        win_text = "🕊 <b>ПОБЕДА МИРНЫХ!</b> Вся мафия уничтожена."
    elif mafia_count >= civil_count:
        winner = "mafia"
        win_text = "🔫 <b>ПОБЕДА МАФИИ!</b> Мафия захватила город."

    if not winner: return False

    # --- РАСКРЫТИЕ РОЛЕЙ ---
    
    role_reveal_text = "\n\n--- 🎭 Роли игроков ---\n"
    
    # Сортируем игроков: мафия (или дон) в начале, затем мирные
    sorted_players = sorted(
        game.players.values(), 
        key=lambda p: p['role'] not in MAFIA_TEAM
    )

    for p in sorted_players:
        # Статус: 💀 если мертв, 🟢 если жив
        status_icon = "🟢" if p['alive'] else "💀"
        role_name = ROLE_NAMES.get(p["role"], p["role"])
        
        role_reveal_text += (
            f"{status_icon} <b>{p['name']}</b>: <i>{role_name}</i>\n"
        )
    
    final_text = win_text + role_reveal_text
    
    # -----------------------

    await bot.send_message(game.chat_id, final_text, parse_mode="HTML")
    
    for uid, p in game.players.items():
        if (winner == "mafia" and p["role"] in MAFIA_TEAM) or \
           (winner == "civilian" and p["role"] not in MAFIA_TEAM):
            stats.inc(uid, "wins")
            
    storage.delete_game(game.chat_id)
    return True

# ---------- НАСТРОЙКИ ----------
@mafia_router.message(Command("settings_mafia"), F.chat.type.in_({"group", "supergroup"}))
async def settings_mafia(msg: types.Message):
    chat_id = msg.chat.id
    game = storage.load_game(chat_id)
    if not game:
        await msg.answer("⚠️ В этом чате ещё нет активной игры.")
        return
    s = game.settings
    text = (
        f"⚙ Настройки игры:\n"
        f"⏱ Время лобби: {s['lobby_time']} сек\n"
        f"🌙 Время ночи: {s['night_time']} сек\n"
        f"🗳 Время голосования: {s['vote_time']} сек\n"
        f"👥 Минимум игроков: {s['min_players']}"
    )
    await msg.answer(text, reply_markup=settings_kb())
    
@mafia_router.callback_query(F.data.startswith("set_"))
async def adjust_settings(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    game = storage.load_game(chat_id)
    if not game: return await call.answer()

    action = call.data
    s = game.settings
    if action == "set_lobby_plus": s["lobby_time"] += 10
    elif action == "set_lobby_minus": s["lobby_time"] = max(10, s["lobby_time"] - 10)
    elif action == "set_night_plus": s["night_time"] += 5
    elif action == "set_night_minus": s["night_time"] = max(5, s["night_time"] - 5)
    elif action == "set_vote_plus": s["vote_time"] += 5
    elif action == "set_vote_minus": s["vote_time"] = max(5, s["vote_time"] - 5)
    elif action == "set_min_plus": s["min_players"] += 1
    elif action == "set_min_minus": s["min_players"] = max(2, s["min_players"] - 1)

    storage.save_game(game)
    text = (
        f"⚙ Настройки игры:\n"
        f"⏱ Время лобби: {s['lobby_time']} сек\n"
        f"🌙 Время ночи: {s['night_time']} сек\n"
        f"🗳 Время голосования: {s['vote_time']} сек\n"
        f"👥 Минимум игроков: {s['min_players']}"
    )
    await call.message.edit_text(text, reply_markup=settings_kb())
    await call.answer("✅ Настройки обновлены")


# ---------- УДАЛЕНИЕ СООБЩЕНИЙ НОЧЬЮ И ОТ МЕРТВЫХ ----------
@mafia_router.message(F.chat.type != "private")
async def delete_messages_check(msg: types.Message):
    """
    Удаляет все сообщения, если:
    1. Идет фаза 'night' (для всех).
    2. Игрок мертв и это не его "последнее слово".
    """
    chat_id = msg.chat.id
    game = storage.load_game(chat_id)

    if not game or game.lobby_open:
        return

    uid = str(msg.from_user.id)
    
    # Игнорируем команды и сообщения от самого бота
    if msg.text and msg.text.startswith('/') or uid == str(msg.bot.id):
        return 

    should_delete = False
    
    # 1. Если фаза НОЧЬ (запрет для всех)
    if game.phase == "night":
        should_delete = True
        
    # 2. Если игрок МЕРТВ
    if uid in game.players and not game.players[uid]["alive"]:
        if game.players[uid].get('last_word_allowed', False):
            # Это "последнее слово" - разрешаем, но сбрасываем флаг
            game.players[uid]['last_word_allowed'] = False
            storage.save_game(game)
            return 
        
        # Если не ночь и не последнее слово - удаляем
        should_delete = True

    if should_delete:
        try:
            await msg.delete()
        except TelegramForbiddenError:
            print(f"Ошибка удаления: У бота нет прав администратора в чате {chat_id}")
            pass
        except Exception:
            pass

# ---------- ЧАТ МАФИИ (ПЕРЕСЫЛКА) ----------
@mafia_router.message(F.chat.type == "private")
async def private_chat_handler(msg: types.Message):
    """Обрабатывает сообщения в ЛС бота для чата мафии"""
    user_id = str(msg.from_user.id)
    
    active_games = storage.get_all_games()
    
    found_game = None
    for gid, game in active_games.items():
        if user_id in game.players and not game.lobby_open:
            player_data = game.players.get(user_id)
            if player_data and player_data["alive"] and player_data["role"] in MAFIA_TEAM and game.phase == "night":
                found_game = game
                break
    
    if not found_game:
        return

    player = found_game.players[user_id]
    
    team = [uid for uid, p in found_game.players.items() if p["role"] in MAFIA_TEAM and p["alive"]] 
    role_title = "Дон" if player["role"] == "don" else "Мафия"
    
    safe_text = html.escape(msg.text)
    text_to_send = f"🎭 <b>{role_title} ({player['name']}):</b> {safe_text}"
    
    for partner_id in team:
        if partner_id != user_id: 
            try:
                await msg.bot.send_message(partner_id, text_to_send, parse_mode="HTML")
            except TelegramForbiddenError:
                pass
            except Exception:
                pass