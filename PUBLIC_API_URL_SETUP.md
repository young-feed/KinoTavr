# Настройка PUBLIC_API_URL для Mini App

## Проблема

Mini App работает в **браузере пользователя**, а не на сервере. Поэтому внутренние Docker URL (например, `http://ai_backend:8001/chat`) не работают — браузер не может обратиться к внутренним контейнерам.

## Решение

Используется две переменные:
- **API_URL** — внутренний Docker URL для бота (`http://ai_backend:8001/chat`)
- **PUBLIC_API_URL** — публичный URL для Mini App, доступный из браузера пользователя

## Настройка для разных сценариев

### 1. Локальная разработка (localhost)

В `.env`:
```env
PUBLIC_API_URL=http://localhost:8001/chat
```

AI backend доступен на `localhost:8001` с хоста.

### 2. Разработка с ngrok

Если AI backend тоже нужен через ngrok:

```bash
# Запустите ngrok для AI backend
ngrok http 8001 --log=stdout > /var/log/ngrok-api.log 2>&1 &

# Получите URL
curl http://localhost:4041/api/tunnels | jq -r '.tunnels[0].public_url'
```

В `.env`:
```env
PUBLIC_API_URL=https://your-ngrok-api-url.ngrok-free.app/chat
```

### 3. Production (VPS с доменом)

Настройте Nginx для проксирования API:

**nginx.conf:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Mini App
    location / {
        proxy_pass http://localhost:8080;
    }

    # API endpoint для Mini App
    location /api/ {
        proxy_pass http://localhost:8001/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

В `.env`:
```env
PUBLIC_API_URL=https://yourdomain.com/api/chat
WEBAPP_URL=https://yourdomain.com
```

### 4. Production (API на отдельном домене)

Если у вас API на отдельном домене:

В `.env`:
```env
PUBLIC_API_URL=https://api.yourdomain.com/chat
WEBAPP_URL=https://app.yourdomain.com
```

**Важно:** Настройте CORS на API backend, чтобы разрешить запросы от `https://app.yourdomain.com`

## Проверка

### 1. Откройте Mini App в браузере
Через Telegram или напрямую через ngrok URL

### 2. Откройте DevTools (F12) → Network
Посмотрите на запросы к API

### 3. Должны видеть запросы к PUBLIC_API_URL
Например: `https://yourdomain.com/api/chat`

### 4. Если видите ошибку CORS
Добавьте в AI backend CORS headers:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Или "*" для разработки
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Troubleshooting

### Ошибка: "Failed to fetch"
- Проверьте что PUBLIC_API_URL доступен из браузера
- Откройте `https://your-public-api-url/chat` в браузере напрямую
- Проверьте CORS настройки

### Ошибка: "net::ERR_CONNECTION_REFUSED"
- API backend не запущен или недоступен по PUBLIC_API_URL
- Проверьте firewall/порты

### Работает в чате, но не в Mini App
- В чате используется API_URL (внутренний Docker)
- В Mini App используется PUBLIC_API_URL (публичный)
- Убедитесь что PUBLIC_API_URL настроен правильно

## Быстрая проверка на сервере

```bash
# 1. Проверьте что API доступен локально
curl http://localhost:8001/ping

# 2. Проверьте что API доступен через публичный URL
curl https://yourdomain.com/api/ping

# 3. Посмотрите логи
docker-compose logs -f ai_backend
docker-compose logs -f telegram_bot
```
