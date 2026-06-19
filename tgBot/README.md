# Кинотавр - Telegram Movie Bot with Mini App

Telegram бот для подбора фильмов с современным Mini App интерфейсом.

## Возможности

- 🎬 Интерактивный подбор фильмов на основе настроения
- 🎨 Динамический градиентный фон (цвет от бэкенда)
- 📱 Telegram Mini App с современным UI
- 📜 История подобранных фильмов
- 🔄 Сброс диалога и начало нового поиска

## Установка

1. Установите зависимости:
```bash
pip install aiogram aiohttp python-dotenv
```

2. Настройте `.env` файл:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
API_URL=http://localhost:7777
WEBAPP_URL=http://localhost:8080
```

## Запуск

### Локальная разработка

1. Запустите бота:
```bash
python main.py
```

Бот запустит встроенный веб-сервер на `http://localhost:8080` для Mini App.

2. Для доступа из Telegram используйте ngrok:
```bash
ngrok http 8080
```

3. Обновите `WEBAPP_URL` в `.env` на URL от ngrok (например, `https://abc123.ngrok.io`).

### Продакшн

Для продакшена разверните Mini App на реальном сервере с HTTPS:
- Используйте Nginx для обслуживания статических файлов из `miniapp/`
- Обновите `WEBAPP_URL` на реальный домен
- Убедитесь, что API доступен по HTTPS

## Структура проекта

```
tgBot/
├── main.py                      # Основной файл бота
├── miniapp/
│   ├── templates/
│   │   └── index.html          # HTML Mini App
│   └── static/
│       ├── css/
│       │   └── style.css       # Стили (Telegram UI)
│       └── js/
│           └── app.js          # Логика приложения
├── .env                         # Настройки окружения
└── README.md                    # Документация
```

## Mini App функции

- **Чат интерфейс**: Общение с ботом в стиле Telegram
- **Градиентный фон**: Меняется на основе цвета от бэкенда
- **История**: Все подобранные фильмы сохраняются локально
- **Сброс диалога**: Начать новый поиск фильма
- **Адаптивный дизайн**: Работает на всех устройствах

## API интеграция

Mini App взаимодействует с тем же API, что и бот:

**Endpoint**: `POST API_URL`

**Payload**:
```json
{
  "user_id": "telegram_user_id",
  "consversion": [
    {
      "question": "bot question",
      "answer": "user answer"
    }
  ]
}
```

**Response**:
```json
{
  "action": "ask|recommend|error",
  "text": "response text",
  "color": "#hexcolor",
  "movie": {
    "title": "Movie Title",
    "year": "2024",
    "description": "Description",
    "kp_url": "https://...",
    "rutube_url": "https://..."
  }
}
```

## Разработка

Для локальной разработки Mini App:

1. Измените файлы в `miniapp/static/`
2. Перезапустите бота
3. Обновите Mini App в Telegram (закройте и откройте заново)

## Telegram Mini App SDK

Приложение использует официальный [Telegram WebApp SDK](https://core.telegram.org/bots/webapps) для:
- Определения темы пользователя
- Показа нативных диалогов
- Открытия ссылок
- Доступа к данным пользователя
