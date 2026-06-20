# Быстрый старт с ngrok

## Шаг 1: Получите ngrok authtoken

1. Зарегистрируйтесь на https://ngrok.com
2. Получите authtoken: https://dashboard.ngrok.com/get-started/your-authtoken

## Шаг 2: Настройте .env

Скопируйте пример:
```bash
cp .env.example .env
```

Отредактируйте `.env`:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_openai_key
NGROK_AUTHTOKEN=your_ngrok_token
WEBAPP_URL=http://localhost:8081  # Обновится автоматически
```

## Шаг 3: Запустите все сервисы

```bash
# Запуск всех сервисов (включая ngrok)
docker-compose up -d
```

## Шаг 4: Обновите WEBAPP_URL автоматически

```bash
# Сделайте скрипт исполняемым (только один раз)
chmod +x update_webapp_url.sh

# Запустите скрипт
./update_webapp_url.sh
```

Скрипт автоматически:
- Получит публичный URL от ngrok
- Обновит `.env` файл
- Перезапустит бота

## Шаг 5: Проверьте работу

1. **ngrok dashboard:** http://localhost:4040
2. **Ваш Mini App:** Откройте URL из вывода скрипта
3. **Telegram бот:** Отправьте `/start` и нажмите "🎬 Открыть Кинотавр"

## Полезные команды

```bash
# Посмотреть логи бота
docker-compose logs -f telegram_bot

# Посмотреть логи ngrok
docker-compose logs -f ngrok

# Получить текущий ngrok URL
curl http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'

# Перезапустить только бота
docker-compose restart telegram_bot

# Остановить все
docker-compose down
```

## Production

Для продакшена используйте реальный домен вместо ngrok.  
См. документацию в `NGROK_SETUP.md` раздел "Production".
