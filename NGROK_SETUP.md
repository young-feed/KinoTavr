# Настройка ngrok для Telegram Bot в Docker

## Вариант 1: ngrok как Docker сервис (Рекомендуется)

### 1. Добавьте ngrok в `docker-compose.yml`

```yaml
  # 6. ngrok для Mini App
  ngrok:
    image: ngrok/ngrok:latest
    container_name: kinotavr_ngrok
    restart: unless-stopped
    command:
      - "http"
      - "telegram_bot:8081"
      - "--authtoken=${NGROK_AUTHTOKEN}"
      - "--log=stdout"
    ports:
      - "4040:4040"  # ngrok web interface
    depends_on:
      - telegram_bot
    environment:
      - NGROK_AUTHTOKEN=${NGROK_AUTHTOKEN}
```

### 2. Получите authtoken от ngrok

1. Зарегистрируйтесь на https://ngrok.com
2. Получите authtoken: https://dashboard.ngrok.com/get-started/your-authtoken
3. Добавьте в `.env` файл:

```env
NGROK_AUTHTOKEN=your_ngrok_authtoken_here
```

### 3. Обновите переменные окружения

Добавьте в `.env`:
```env
TELEGRAM_BOT_TOKEN=8534661552:AAGZ1ykDRGnprGx0OuE9aQxTbGal56y0Du0
OPENAI_API_KEY=your_openai_key
NGROK_AUTHTOKEN=your_ngrok_token
WEBAPP_URL=https://your-ngrok-url.ngrok-free.app
```

### 4. Запустите все сервисы

```bash
docker-compose up -d
```

### 5. Получите ngrok URL

```bash
# Откройте ngrok web interface
curl http://localhost:4040/api/tunnels | jq

# Или посмотрите в браузере
# http://localhost:4040
```

### 6. Обновите WEBAPP_URL

После запуска получите публичный URL ngrok и обновите `.env`:
```env
WEBAPP_URL=https://abc123.ngrok-free.app
```

Затем перезапустите бота:
```bash
docker-compose restart telegram_bot
```

---

## Вариант 2: ngrok с постоянным доменом (Платный план)

Если у вас платный ngrok план с кастомным доменом:

```yaml
  ngrok:
    image: ngrok/ngrok:latest
    container_name: kinotavr_ngrok
    restart: unless-stopped
    command:
      - "http"
      - "telegram_bot:8081"
      - "--authtoken=${NGROK_AUTHTOKEN}"
      - "--domain=your-custom-domain.ngrok-free.app"
    ports:
      - "4040:4040"
    depends_on:
      - telegram_bot
```

В `.env`:
```env
WEBAPP_URL=https://your-custom-domain.ngrok-free.app
```

---

## Вариант 3: ngrok отдельно на хосте (без Docker)

### 1. Установите ngrok на сервере

```bash
# Ubuntu/Debian
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
  sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && \
  echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
  sudo tee /etc/apt/sources.list.d/ngrok.list && \
  sudo apt update && sudo apt install ngrok
```

### 2. Настройте authtoken

```bash
ngrok config add-authtoken YOUR_AUTHTOKEN
```

### 3. Запустите ngrok

```bash
ngrok http 8080 --log=stdout > /var/log/ngrok.log 2>&1 &
```

Или создайте systemd сервис `/etc/systemd/system/ngrok.service`:

```ini
[Unit]
Description=ngrok tunnel
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/ngrok http 8080 --log=stdout
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запустите:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ngrok
sudo systemctl start ngrok
```

### 4. Получите URL

```bash
curl http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'
```

---

## Автоматическое обновление WEBAPP_URL

Создайте скрипт `update_webapp_url.sh`:

```bash
#!/bin/bash

# Получаем ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')

if [ -z "$NGROK_URL" ] || [ "$NGROK_URL" == "null" ]; then
    echo "Error: Cannot get ngrok URL"
    exit 1
fi

echo "New ngrok URL: $NGROK_URL"

# Обновляем .env
sed -i "s|WEBAPP_URL=.*|WEBAPP_URL=$NGROK_URL|g" .env

# Перезапускаем бота
docker-compose restart telegram_bot

echo "Bot restarted with new URL: $NGROK_URL"
```

Сделайте исполняемым:
```bash
chmod +x update_webapp_url.sh
```

Добавьте в crontab для автозапуска после перезагрузки:
```bash
@reboot sleep 30 && /path/to/update_webapp_url.sh
```

---

## Проверка работы

1. **Проверьте ngrok web interface:**
   ```bash
   curl http://localhost:4040/api/tunnels
   ```

2. **Проверьте Mini App:**
   ```
   https://your-ngrok-url.ngrok-free.app
   ```

3. **Проверьте бота в Telegram:**
   - Отправьте `/start`
   - Нажмите кнопку "🎬 Открыть Кинотавр"

---

## Проблемы и решения

### ngrok показывает "ERR_NGROK_3200"
- Проверьте authtoken: `ngrok config check`
- Убедитесь что бот запущен на порту 8081

### Mini App не открывается
- Проверьте WEBAPP_URL в .env
- Убедитесь что ngrok tunnel активен: `curl http://localhost:4040/api/tunnels`
- Проверьте логи бота: `docker logs kinotavr_telegram_bot`

### URL меняется после перезагрузки
- Используйте платный ngrok план с кастомным доменом
- Или настройте автообновление через `update_webapp_url.sh`

---

## Production: Замена ngrok на реальный домен

Для продакшена вместо ngrok используйте:

1. **Купите домен** (например, на Namecheap, GoDaddy)
2. **Настройте DNS** A-запись на IP сервера
3. **Настройте Nginx** как reverse proxy
4. **Получите SSL** через Let's Encrypt

См. файл `VPS_DEPLOYMENT.md` для подробной инструкции.
