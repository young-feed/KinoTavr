import asyncio
import os
import logging
import aiohttp
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from collections import defaultdict
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from aiohttp import web

load_dotenv()

# Настройки
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("API_URL")  # Internal Docker URL for bot
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", API_URL)  # Public URL for Mini App (browser)
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.com")  # URL где будет размещено приложение

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Временное хранилище сессий (для продакшена лучше использовать Redis или БД)
# Структура: {user_id: {"history": [], "last_question": "", "movies": [], "last_request_time": timestamp}}
user_sessions = {}

# Rate limiting
rate_limit_store = defaultdict(list)
RATE_LIMIT_REQUESTS = 10  # Максимум запросов
RATE_LIMIT_WINDOW = 60  # За 60 секунд

# Notification system
user_notification_preferences = {}  # {user_id: {"enabled": bool, "last_notified": timestamp}}

# Bot menu commands
async def set_bot_commands(bot: Bot):
    """Установка меню команд бота"""
    commands = [
        types.BotCommand(command="start", description="🎬 Начать работу с ботом"),
        types.BotCommand(command="help", description="❓ Помощь по использованию"),
        types.BotCommand(command="history", description="📚 История подобранных фильмов"),
        types.BotCommand(command="stats", description="📊 Ваша статистика"),
        types.BotCommand(command="notify", description="🔔 Настроить напоминания"),
    ]
    await bot.set_my_commands(commands)


def check_rate_limit(user_id: int) -> bool:
    """Проверка rate limit для пользователя"""
    now = datetime.now()

    # Очищаем старые записи
    rate_limit_store[user_id] = [
        timestamp for timestamp in rate_limit_store[user_id]
        if now - timestamp < timedelta(seconds=RATE_LIMIT_WINDOW)
    ]

    # Проверяем лимит
    if len(rate_limit_store[user_id]) >= RATE_LIMIT_REQUESTS:
        return False

    # Добавляем новый запрос
    rate_limit_store[user_id].append(now)
    return True


def validate_webapp_data(init_data: str, bot_token: str) -> bool:
    """Валидация данных от Telegram WebApp"""
    try:
        # Парсим query string
        parsed = dict(param.split('=', 1) for param in init_data.split('&'))

        if 'hash' not in parsed:
            return False

        received_hash = parsed.pop('hash')

        # Создаем строку для проверки
        data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(parsed.items()))

        # Вычисляем секретный ключ
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode(),
            digestmod=hashlib.sha256
        ).digest()

        # Вычисляем хеш
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        return calculated_hash == received_hash
    except Exception as e:
        logging.error(f"WebApp validation error: {e}")
        return False


async def send_to_backend(user_id: int, history: list) -> dict:
    """Функция для отправки запроса к FastAPI бэкенду"""
    payload = {
        "user_id": user_id,
        "consversion": history  # Используем опечатку из бэкенда для совместимости
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(API_URL, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logging.error(f"Backend error: {response.status}")
                    return {"action": "error", "text": "Произошла ошибка на сервере."}
        except Exception as e:
            logging.error(f"Connection error: {e}")
            return {"action": "error", "text": "Не удалось связаться с мозговым центром."}


@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id

    # Очищаем историю при новом старте
    user_sessions[user_id] = {"history": [], "last_question": "", "movies": []}

    welcome_text = (
        "🎬 <b>Привет! Я Кинотавр</b>\n\n"
        "Я помогу тебе подобрать фильм под настроение!\n\n"
        "Просто напиши, как себя чувствуешь или что хочешь от фильма на вечер, "
        "и я найду идеальный вариант 🍿\n\n"
        "💡 <i>Для лучшего опыта открой Mini App ниже!</i>"
    )

    # Создаем кнопку для Mini App
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🎬 Открыть Кинотавр",
        web_app=WebAppInfo(url=WEBAPP_URL)
    )

    await message.answer(welcome_text, reply_markup=builder.as_markup(), parse_mode="HTML")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = (
        "❓ <b>Как пользоваться ботом</b>\n\n"
        "1️⃣ Напиши мне о своем настроении или предпочтениях\n"
        "2️⃣ Я задам уточняющие вопросы, если нужно\n"
        "3️⃣ Получи идеальный фильм под твое настроение!\n\n"
        "<b>Команды:</b>\n"
        "/start - Начать заново\n"
        "/history - Посмотреть историю фильмов\n"
        "/stats - Посмотреть статистику\n"
        "/help - Эта справка\n\n"
        "💡 <b>Примеры запросов:</b>\n"
        "• \"Хочу что-то веселое\"\n"
        "• \"Грустно сегодня\"\n"
        "• \"Посоветуй детектив\"\n"
        "• \"Что-то с адреналином\""
    )
    await message.answer(help_text, parse_mode="HTML")


@dp.message(Command("history"))
async def cmd_history(message: Message):
    """Обработчик команды /history"""
    user_id = message.from_user.id

    if user_id not in user_sessions or not user_sessions[user_id].get("movies"):
        await message.answer(
            "📚 <b>История пока пуста</b>\n\n"
            "Найденные фильмы будут отображаться здесь.",
            parse_mode="HTML"
        )
        return

    movies = user_sessions[user_id]["movies"][-10:]  # Последние 10 фильмов
    history_text = "📚 <b>Последние подобранные фильмы:</b>\n\n"

    for idx, movie in enumerate(reversed(movies), 1):
        title = movie.get("title", "Неизвестный фильм")
        year = movie.get("year", "")
        history_text += f"{idx}. 🍿 <b>{title}</b> {f'({year})' if year else ''}\n"

    history_text += "\n💡 <i>Откройте Mini App для полной истории с описаниями</i>"

    # Кнопка для открытия Mini App
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📖 Открыть полную историю",
        web_app=WebAppInfo(url=WEBAPP_URL)
    )

    await message.answer(history_text, reply_markup=builder.as_markup(), parse_mode="HTML")


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Обработчик команды /stats"""
    user_id = message.from_user.id

    if user_id not in user_sessions:
        total_movies = 0
    else:
        total_movies = len(user_sessions[user_id].get("movies", []))

    stats_text = (
        f"📊 <b>Ваша статистика</b>\n\n"
        f"🎬 Подобрано фильмов: <b>{total_movies}</b>\n"
    )

    if total_movies > 0:
        stats_text += f"\n🌟 Продолжайте искать отличное кино!"
    else:
        stats_text += f"\n💡 Начните диалог, чтобы получить первую рекомендацию!"

    await message.answer(stats_text, parse_mode="HTML")


@dp.message(Command("notify"))
async def cmd_notify(message: Message):
    """Обработчик команды /notify - настройка напоминаний"""
    user_id = message.from_user.id

    # Проверяем текущее состояние
    is_enabled = user_notification_preferences.get(user_id, {}).get("enabled", False)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔔 Включить" if not is_enabled else "🔕 Выключить",
                callback_data="toggle_notifications"
            )
        ]
    ])

    status = "включены ✅" if is_enabled else "выключены ❌"

    notify_text = (
        f"🔔 <b>Напоминания</b>\n\n"
        f"Статус: {status}\n\n"
        f"Когда включены, я буду напоминать вам о выборе фильма, "
        f"если вы давно не заходили в бот.\n\n"
        f"Напоминания приходят не чаще раза в 3 дня."
    )

    await message.answer(notify_text, parse_mode="HTML", reply_markup=keyboard)


@dp.callback_query(F.data == "toggle_notifications")
async def callback_toggle_notifications(callback: CallbackQuery):
    """Обработчик переключения уведомлений"""
    await callback.answer()

    user_id = callback.from_user.id

    # Инициализируем или получаем текущее состояние
    if user_id not in user_notification_preferences:
        user_notification_preferences[user_id] = {"enabled": False, "last_notified": None}

    # Переключаем состояние
    current_state = user_notification_preferences[user_id]["enabled"]
    user_notification_preferences[user_id]["enabled"] = not current_state

    new_state = user_notification_preferences[user_id]["enabled"]
    status = "включены ✅" if new_state else "выключены ❌"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔔 Включить" if not new_state else "🔕 Выключить",
                callback_data="toggle_notifications"
            )
        ]
    ])

    notify_text = (
        f"🔔 <b>Напоминания</b>\n\n"
        f"Статус: {status}\n\n"
        f"Когда включены, я буду напоминать вам о выборе фильма, "
        f"если вы давно не заходили в бот.\n\n"
        f"Напоминания приходят не чаще раза в 3 дня."
    )

    await callback.message.edit_text(notify_text, parse_mode="HTML", reply_markup=keyboard)


@dp.message()
async def process_user_message(message: Message):
    """Обработчик всех текстовых сообщений пользователя"""
    user_id = message.from_user.id
    user_text = message.text

    # Проверка rate limit
    if not check_rate_limit(user_id):
        await message.answer(
            "⏱ <b>Слишком много запросов</b>\n\n"
            "Пожалуйста, подождите немного перед следующим сообщением.",
            parse_mode="HTML"
        )
        logging.warning(f"Rate limit exceeded for user {user_id}")
        return

    # Инициализируем сессию, если вдруг ее нет
    if user_id not in user_sessions:
        user_sessions[user_id] = {"history": [], "last_question": "", "movies": []}

    session = user_sessions[user_id]

    # Формируем пару "предыдущий вопрос бота - текущий ответ юзера"
    message_pair = {
        "question": session["last_question"],
        "answer": user_text
    }

    # Добавляем в историю
    session["history"].append(message_pair)

    # Чтобы контекст не разрастался бесконечно, можно ограничить историю (например, 5 последних пар)
    # if len(session["history"]) > 5:
    #   session["history"].pop(0)

    # Отправляем "typing..." пока ждем ответ от ИИ
    await bot.send_chat_action(chat_id=user_id, action="typing")

    # Получаем ответ от бэкенда
    backend_response = await send_to_backend(user_id, session["history"])

    action = backend_response.get("action")
    response_text = backend_response.get("text", "Извини, я немного задумался. Повторишь?")

    if action == "ask":
        # Бот задает уточняющий вопрос. Обновляем last_question
        session["last_question"] = response_text
        await message.answer(response_text)

    elif action == "recommend":
        # ИИ определил настроение и выдал рекомендацию
        movie_data = backend_response.get("movie")

        if movie_data:
            # Сохраняем фильм в историю пользователя
            session["movies"].append(movie_data)

            # Парсим данные фильма
            title = movie_data.get("title", "Неизвестный фильм")
            description = movie_data.get("description", "Описание отсутствует.")
            year = movie_data.get("year", "")
            poster_url = movie_data.get("poster_url", "")
            kp_url = movie_data.get("kp_url", "")
            rutube_url = movie_data.get("rutube_url", "")

            # Формируем сообщение с фильмом
            final_message = f"{response_text}\n\n"
            final_message += f"🍿 <b>{title}</b> {f'({year})' if year else ''}\n"
            final_message += f"📝 {description}\n\n"

            # Добавляем ссылки если есть
            links = []
            if kp_url:
                links.append(f'<a href="{kp_url}">Кинопоиск</a>')
            if rutube_url:
                links.append(f'<a href="{rutube_url}">Смотреть на Rutube</a>')

            if links:
                final_message += "🔗 " + " | ".join(links)

            # Создаем inline кнопки
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 Начать заново", callback_data="restart"),
                    InlineKeyboardButton(text="🎬 Открыть Mini App", web_app=WebAppInfo(url=WEBAPP_URL))
                ]
            ])

            await message.answer(final_message, parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=False)

            # Сбрасываем историю диалога после успешной рекомендации
            user_sessions[user_id]["history"] = []
            user_sessions[user_id]["last_question"] = ""
        else:
            await message.answer(
                f"{response_text}\n\nК сожалению, в базе пока нет подходящего фильма для этого настроения 😔",
                parse_mode="HTML"
            )
            # Сбрасываем историю
            user_sessions[user_id]["history"] = []
            user_sessions[user_id]["last_question"] = ""

    else:
        # Обработка ошибок
        await message.answer(response_text)


# Обработчики callback-кнопок
@dp.callback_query(F.data == "restart")
async def callback_restart(callback: CallbackQuery):
    """Обработчик кнопки 'Начать заново'"""
    await callback.answer()

    user_id = callback.from_user.id
    user_sessions[user_id] = {"history": [], "last_question": "", "movies": user_sessions.get(user_id, {}).get("movies", [])}

    await callback.message.answer(
        "🔄 <b>Начинаем заново!</b>\n\n"
        "Расскажи, какое у тебя сейчас настроение?",
        parse_mode="HTML"
    )


# Web server для обслуживания Mini App
async def webapp_handler(request):
    """Обработчик для главной страницы Mini App"""
    with open('miniapp/templates/index.html', 'r', encoding='utf-8') as f:
        html = f.read()
        # Replace API_URL placeholder with PUBLIC_API_URL (accessible from browser)
        html = html.replace('API_URL_PLACEHOLDER', PUBLIC_API_URL)
    return web.Response(text=html, content_type='text/html')


async def serve_static(request):
    """Обработчик для статических файлов"""
    filename = request.match_info['filename']
    filepath = os.path.join('miniapp', 'static', filename)

    if not os.path.exists(filepath):
        return web.Response(status=404, text='File not found')

    # Determine content type
    content_type = 'text/plain'
    if filename.endswith('.css'):
        content_type = 'text/css'
    elif filename.endswith('.js'):
        content_type = 'application/javascript'
    elif filename.endswith('.svg'):
        content_type = 'image/svg+xml'
    elif filename.endswith('.png'):
        content_type = 'image/png'
    elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
        content_type = 'image/jpeg'

    # Read binary for images, text for others
    if filename.endswith(('.png', '.jpg', '.jpeg')):
        with open(filepath, 'rb') as f:
            content = f.read()
        return web.Response(body=content, content_type=content_type)
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace API_URL placeholder in JavaScript
        if filename.endswith('.js'):
            content = content.replace('API_URL_PLACEHOLDER', PUBLIC_API_URL)

        return web.Response(text=content, content_type=content_type)


async def init_webapp():
    """Инициализация веб-сервера для Mini App"""
    app = web.Application()
    app.router.add_get('/', webapp_handler)
    app.router.add_get('/static/{filename:.*}', serve_static)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, '0.0.0.0', 8081)
    await site.start()

    logging.info("WebApp server started at http://0.0.0.0:8081")


async def main():
    logging.basicConfig(level=logging.INFO)

    # Устанавливаем команды бота
    await set_bot_commands(bot)

    # Запускаем веб-сервер для Mini App (для локальной разработки)
    # В продакшене используйте ngrok или разверните на реальном сервере
    await init_webapp()

    # Запускаем фоновую задачу для отправки уведомлений
    asyncio.create_task(notification_scheduler())

    logging.info("Starting Telegram Bot...")
    await dp.start_polling(bot)


async def notification_scheduler():
    """Фоновая задача для отправки периодических напоминаний"""
    while True:
        try:
            await asyncio.sleep(3600)  # Проверяем каждый час

            now = datetime.now()

            for user_id, preferences in user_notification_preferences.items():
                if not preferences.get("enabled", False):
                    continue

                last_notified = preferences.get("last_notified")

                # Если прошло больше 3 дней с последнего уведомления
                if last_notified is None or (now - last_notified) > timedelta(days=3):
                    try:
                        await bot.send_message(
                            user_id,
                            "🎬 <b>Давненько не виделись!</b>\n\n"
                            "Может быть, пора выбрать новый фильм на вечер? 🍿\n\n"
                            "Просто напиши мне о своем настроении!",
                            parse_mode="HTML"
                        )
                        user_notification_preferences[user_id]["last_notified"] = now
                        logging.info(f"Sent notification to user {user_id}")
                    except Exception as e:
                        logging.error(f"Failed to send notification to {user_id}: {e}")

        except Exception as e:
            logging.error(f"Error in notification scheduler: {e}")


if __name__ == "__main__":
    asyncio.run(main())
