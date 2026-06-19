# Кинотавр - Telegram Bot

## Структура проекта

```
AI_Cinema228/
├── main.py                 # FastAPI бэкенд с AI
├── tg_bot/
│   ├── main.py            # Telegram бот
│   ├── .env               # Настройки бота
│   └── requirements.txt   # Зависимости бота
├── .env                   # Настройки бэкенда
├── requirements.txt       # Зависимости бэкенда
└── start_backend.bat      # Запуск бэкенда
```

## Как запустить

### Шаг 1: Запустить FastAPI бэкенд
Откройте первый терминал:
```bash
cd D:\AI_Cinema228
start_backend.bat
```

Или вручную:
```bash
.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 7777 --reload
```

Проверьте что бэкенд работает: http://localhost:7777/ping

### Шаг 2: Запустить Telegram бота
Откройте второй терминал:
```bash
cd D:\AI_Cinema228
.venv\Scripts\python.exe tg_bot\main.py
```

Или используйте bat-файл:
```bash
cd tg_bot
start_bot.bat
```

## Что исправлено

1. ✅ Установлены зависимости: `aiogram`, `aiohttp`
2. ✅ Исправлен URL эндпоинта: `/chat` вместо корня
3. ✅ Созданы скрипты для запуска

## Настройки

### tg_bot/.env
```
TELEGRAM_BOT_TOKEN=8534661552:AAGZ1ykDRGnprGx0OuE9aQxTbGal56y0Du0
API_URL=http://localhost:7777/chat
```

### .env (корневой)
```
OPENAI_API_KEY=gsk_...
DB_HOST=localhost
DB_NAME=movies_db
DB_USER=user_admin
DB_PASSWORD=super_secure_password
DB_PORT=5432
```

## Проверка работы

1. Запустите бэкенд → должен ответить на http://localhost:7777/ping
2. Запустите бота → в консоли появится "Starting Telegram Bot..."
3. Напишите боту в Telegram: /start
4. Бот должен ответить приветствием

## Возможные проблемы

- **База данных не работает**: Убедитесь что PostgreSQL запущен и настроен
- **Бэкенд не отвечает**: Проверьте порт 7777 (может быть занят)
- **Бот не отвечает**: Проверьте токен в tg_bot/.env
